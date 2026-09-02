#include <zlib.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

constexpr int64_t US=1000000LL;
constexpr int64_t MAX_WINDOW_US=32LL*US;
constexpr double EPS=1e-12;

const std::array<int,10> COUNTS={{14,6,10,6,20,40,6,8,8,12}};

struct Row{
  int64_t exchange_ts=0, local_ts=0;
  bool snapshot=false,bid=false;
  double price=0,amount=0;
};

struct Book{
  std::map<double,double,std::greater<double>> bids;
  std::map<double,double> asks;
  bool ready=false;
  void clear(){bids.clear();asks.clear();ready=false;}
  double qty(bool bid,double p)const{
    if(bid){auto it=bids.find(p);return it==bids.end()?0.0:it->second;}
    auto it=asks.find(p);return it==asks.end()?0.0:it->second;
  }
  bool structurally_valid()const{
    if(bids.empty()||asks.empty())return false;
    return bids.begin()->first>0 && asks.begin()->first>bids.begin()->first;
  }
  bool valid()const{return ready&&structurally_valid();}
  double mid()const{return(valid()? (bids.begin()->first+asks.begin()->first)/2.0:
                       std::numeric_limits<double>::quiet_NaN());}
};

void apply(Book&b,const Row&r){
  if(r.bid){
    if(r.amount==0)b.bids.erase(r.price); else b.bids[r.price]=r.amount;
  }else{
    if(r.amount==0)b.asks.erase(r.price); else b.asks[r.price]=r.amount;
  }
}

bool parse_bool(const char*s,size_t n){return n==4&&(s[0]=='t'||s[0]=='T');}
bool parse_row(const std::string&line,Row&out){
  std::array<std::pair<const char*,size_t>,8> f{};
  size_t field=0,start=0;
  for(size_t i=0;i<=line.size();++i){
    if(i==line.size()||line[i]==','){
      if(field>=f.size())return false;
      f[field++]={line.data()+start,i-start};start=i+1;
    }
  }
  if(field!=8)return false;
  try{
    out.exchange_ts=std::stoll(std::string(f[2].first,f[2].second));
    out.local_ts=std::stoll(std::string(f[3].first,f[3].second));
    out.snapshot=parse_bool(f[4].first,f[4].second);
    std::string side(f[5].first,f[5].second);
    if(side=="bid")out.bid=true;else if(side=="ask")out.bid=false;else return false;
    out.price=std::stod(std::string(f[6].first,f[6].second));
    out.amount=std::stod(std::string(f[7].first,f[7].second));
  }catch(...){return false;}
  return std::isfinite(out.price)&&out.price>0&&std::isfinite(out.amount)&&out.amount>=0;
}

class GzLineReader{
 public:
  explicit GzLineReader(const std::string&p){
    f_=gzopen(p.c_str(),"rb");if(!f_)throw std::runtime_error("cannot open gzip input");
    buf_.resize(1<<20);
  }
  ~GzLineReader(){if(f_)gzclose(f_);}
  bool getline(std::string&out){
    out.clear();
    while(true){
      char*p=gzgets(f_,buf_.data(),static_cast<int>(buf_.size()));
      if(!p)return !out.empty();
      size_t n=std::char_traits<char>::length(p);out.append(p,n);
      if(n&&p[n-1]=='\n'){
        while(!out.empty()&&(out.back()=='\n'||out.back()=='\r'))out.pop_back();
        return true;
      }
      if(gzeof(f_))return !out.empty();
    }
  }
 private: gzFile f_=nullptr;std::vector<char>buf_;
};

std::vector<int64_t> read_support(const std::string&p){
  std::ifstream in(p);if(!in)throw std::runtime_error("cannot open support");
  std::string line;if(!std::getline(in,line)||line!="local_timestamp_us")throw std::runtime_error("bad support header");
  std::vector<int64_t>x;
  while(std::getline(in,line)){if(!line.empty())x.push_back(std::stoll(line));}
  if(!std::is_sorted(x.begin(),x.end())||std::adjacent_find(x.begin(),x.end())!=x.end())
    throw std::runtime_error("support not unique sorted");
  return x;
}

double imb(double b,double a){double d=b+a;return d>0?(b-a)/d:0;}
double ratio(double n,double d){return d>0?n/d:0;}
double clip(double x,double lo,double hi){return std::max(lo,std::min(hi,x));}

struct Snapshot{
  std::array<double,50> bp{},bq{},ap{},aq{};
  bool ok=false;
  double mid=0,spread=0,spread_bps=0;
};

Snapshot snap50(const Book&b){
  Snapshot s;if(!b.valid()||b.bids.size()<50||b.asks.size()<50)return s;
  int k=0;for(auto it=b.bids.begin();k<50;++it,++k){s.bp[k]=it->first;s.bq[k]=it->second;}
  k=0;for(auto it=b.asks.begin();k<50;++it,++k){s.ap[k]=it->first;s.aq[k]=it->second;}
  s.mid=(s.bp[0]+s.ap[0])/2;s.spread=s.ap[0]-s.bp[0];s.spread_bps=10000*s.spread/s.mid;
  s.ok=std::isfinite(s.mid)&&s.mid>0&&s.spread>0;return s;
}

double sumq(const std::array<double,50>&q,int L){
  return std::accumulate(q.begin(),q.begin()+L,0.0);
}
int insertion_rank(const std::array<double,50>&p,double x,bool bid){
  for(int i=0;i<50;++i){
    if(x==p[i]) return i+1;
    if(bid && x>p[i]) return i+1;
    if(!bid && x<p[i]) return i+1;
  }
  return 51;
}
double ols(const std::vector<double>&x,const std::vector<double>&y){
  if(x.size()!=y.size()||x.size()<2)return 0;
  double mx=std::accumulate(x.begin(),x.end(),0.0)/x.size();
  double my=std::accumulate(y.begin(),y.end(),0.0)/y.size();
  double num=0,den=0;for(size_t i=0;i<x.size();++i){double dx=x[i]-mx;num+=dx*(y[i]-my);den+=dx*dx;}
  return den>0?num/den:0;
}
double microdisp(const Snapshot&s,int L){
  double B=sumq(s.bq,L),A=sumq(s.aq,L),d=A+B;
  double m=d>0?(s.ap[0]*B+s.bp[0]*A)/d:s.mid;
  return 10000*(m-s.mid)/s.mid;
}
std::array<double,2> slopes(const Snapshot&s,int L){
  std::vector<double>bd,ad,by,ay;bd.reserve(L);ad.reserve(L);by.reserve(L);ay.reserve(L);
  for(int i=0;i<L;++i){
    bd.push_back(10000*std::abs(s.bp[i]-s.mid)/s.mid);
    ad.push_back(10000*std::abs(s.ap[i]-s.mid)/s.mid);
    by.push_back(std::log1p(s.bq[i]));ay.push_back(std::log1p(s.aq[i]));
  }
  return {{ols(bd,by),ols(ad,ay)}};
}

enum EC{BI=0,BD=1,BR=2,BP=3,AI=4,AD=5,AR=6,AP=7,NONE=8};

struct Ev{
  int64_t ts=0;EC cls=NONE;double dq=0,absdq=0,normden=0,dist=0;int rank=0;
};
struct Group{
  int64_t ts=0;std::array<int,8>counts{};bool has_dom=false;EC dom=NONE;
  double micro10=0,l1obi=0;Snapshot post;bool valid=false;
};

struct DepthShock{
  int64_t ts=0;bool bid=false;double d0=0,dmin=0;
};
struct SpreadShock{int64_t ts=0;double pre=0,shock=0;};
struct QueueShock{int64_t ts=0;bool bid=false;double pre=0,post=0,minpost=0;};

void append(std::vector<double>&o,const std::vector<double>&x){o.insert(o.end(),x.begin(),x.end());}
void append(std::vector<double>&o,std::initializer_list<double>x){o.insert(o.end(),x.begin(),x.end());}

std::vector<const Ev*> events_in(const std::deque<Ev>&evs,int64_t t,double lo,double hi){
  std::vector<const Ev*>r;for(const auto&e:evs){double age=(t-e.ts)/1e6;if(age>=lo&&age<=hi)r.push_back(&e);}return r;
}
std::vector<const Group*> groups_in(const std::deque<Group>&gs,int64_t t,double maxage=32){
  std::vector<const Group*>r;for(const auto&g:gs){double age=(t-g.ts)/1e6;if(age>=0&&age<=maxage&&g.valid)r.push_back(&g);}return r;
}

double pressure_count(const std::vector<const Ev*>&es,EC b,EC a){
  double nb=0,na=0;for(auto e:es){if(e->cls==b)++nb;else if(e->cls==a)++na;}return imb(nb,na);
}
double pressure_remove(const std::vector<const Ev*>&es,EC b,EC a){
  double nb=0,na=0;for(auto e:es){if(e->cls==b)++nb;else if(e->cls==a)++na;}return imb(na,nb);
}
double expint(const std::deque<Ev>&evs,int64_t t,EC c,double tau){
  double z=0;for(const auto&e:evs)if(e.cls==c){double age=(t-e.ts)/1e6;if(age>=0&&age<=32)z+=std::exp(-age/tau);}return z;
}
double cosine(const std::array<double,10>&a,const std::array<double,10>&b){
  double ab=0,aa=0,bb=0;for(int i=0;i<10;++i){ab+=a[i]*b[i];aa+=a[i]*a[i];bb+=b[i]*b[i];}
  return aa>0&&bb>0?ab/std::sqrt(aa*bb):0;
}

std::vector<double> features(
 const Snapshot&s,int64_t t,const std::deque<Ev>&evs,const std::deque<Group>&groups,
 const std::deque<DepthShock>&dsh,const std::deque<SpreadShock>&ssh,const std::deque<QueueShock>&qsh
){
  (void)ssh;(void)qsh;
  std::vector<double>o;o.reserve(130);
  if(!s.ok)return o;
  auto gs=groups_in(groups,t);
  auto e32=events_in(evs,t,0,32);

  // E2R01 B06 queue imbalance x spread-state interaction.
  const int L7[7]={1,2,3,5,10,20,50};
  double logspread=std::log1p(s.spread_bps);
  for(int L:L7){
    double q=imb(sumq(s.bq,L),sumq(s.aq,L));
    append(o,{q,q*logspread});
  }

  // E2R02 B07 queue-imbalance event-time persistence.
  double current_q=imb(s.bq[0],s.aq[0]);
  if(gs.empty()){
    append(o,{current_q,current_q,0,0,0,0});
  }else{
    std::vector<double>qv,tx;
    qv.reserve(gs.size());tx.reserve(gs.size());
    int64_t t0=gs.front()->ts;
    for(auto g:gs){qv.push_back(g->l1obi);tx.push_back((g->ts-t0)/1e6);}
    double mean=std::accumulate(qv.begin(),qv.end(),0.0)/qv.size(),ss=0;
    for(double q:qv)ss+=(q-mean)*(q-mean);
    double sd=std::sqrt(ss/qv.size());
    auto sgn=[](double x){return x>0?1:(x<0?-1:0);};
    int cs=sgn(current_q),same=0;
    for(double q:qv)if(cs!=0&&sgn(q)==cs&&sgn(q)!=0)++same;
    double samefrac=(double)same/qv.size();
    double persist=0;
    if(qv.size()>=2){
      int n=0;for(size_t i=1;i<qv.size();++i)if(sgn(qv[i])==sgn(qv[i-1]))++n;
      persist=(double)n/(qv.size()-1);
    }
    append(o,{current_q,mean,sd,samefrac,persist,ols(tx,qv)});
  }

  // E2R03 C04 spread-normalized microprice x same-depth OBI.
  const int L5[5]={1,5,10,20,50};
  for(int L:L5){
    double md=microdisp(s,L);
    double nm=s.spread_bps>0?md/s.spread_bps:0;
    double q=imb(sumq(s.bq,L),sumq(s.aq,L));
    append(o,{nm,nm*q});
  }

  // E2R04 C06 microprice acceleration / curvature.
  std::array<double,4>sum{},bm{};std::array<int,4>cnt{};
  for(auto g:gs){
    double age=(t-g->ts)/1e6;
    int b=age<=1?0:(age<=4?1:(age<=16?2:3));
    sum[b]+=g->micro10;cnt[b]++;
  }
  double cur=microdisp(s,10);
  for(int b=0;b<4;++b){
    if(cnt[b]){bm[b]=sum[b]/cnt[b];continue;}
    bool found=false;
    for(int j=b+1;j<4;++j)if(cnt[j]){bm[b]=sum[j]/cnt[j];found=true;break;}
    if(!found)bm[b]=cur;
  }
  double d01=bm[0]-bm[1],d12=bm[1]-bm[2],d23=bm[2]-bm[3];
  // Quadratic OLS coefficient for fixed x={0.5,2.5,10,24}.
  const double qw[4]={0.0041839276956925,0.0004089183034450,-0.0076510031152220,0.0030581571160845};
  double qc=0;for(int i=0;i<4;++i)qc+=qw[i]*bm[i];
  append(o,{d01,d12,d23,d01-d12,d12-d23,qc});

  // E2R05 D08 raw top-20 MLOFI input (PCA fit later, train-only).
  for(int j=1;j<=20;++j){
    double sn=0,ab=0;
    for(auto e:e32)if(e->rank==j){sn+=(e->cls<AI?1:-1)*e->dq;ab+=e->absdq;}
    append(o,{ratio(sn,ab)});
  }

  // E2R06 D09 raw stationary flow input (SVD fit later, train-only).
  for(double w:{1.0,4.0,16.0,32.0})
    for(int j=1;j<=10;++j){
      double sn=0;
      for(auto e:e32)if((t-e->ts)/1e6<=w&&e->rank==j)sn+=(e->cls<AI?1:-1)*e->dq;
      append(o,{sn});
    }

  // E2R07 E08 depth dispersion / weighted variance.
  auto disp=[&](const std::array<double,50>&p,const std::array<double,50>&q){
    double sq=sumq(q,50),mu=0,var=0;
    for(int i=0;i<50;++i){
      double w=q[i]/std::max(sq,EPS);
      double d=10000*std::abs(p[i]-s.mid)/s.mid;
      mu+=w*d;
    }
    for(int i=0;i<50;++i){
      double w=q[i]/std::max(sq,EPS);
      double d=10000*std::abs(p[i]-s.mid)/s.mid;
      var+=w*(d-mu)*(d-mu);
    }
    return std::array<double,2>{{var,std::sqrt(std::max(0.0,var))}};
  };
  auto bd=disp(s.bp,s.bq),ad=disp(s.ap,s.aq);
  append(o,{bd[0],ad[0],ad[0]-bd[0],bd[1],ad[1],ad[1]-bd[1]});

  // E2R08 F09 event-type run lengths / directional sign persistence.
  std::vector<const Group*>dg;for(auto g:gs)if(g->has_dom)dg.push_back(g);
  if(dg.empty()){
    append(o,{0,0,0,0,0,0,0,32});
  }else{
    auto ps=[](EC c){
      return (c==BI||c==BR||c==AD||c==AP)?1:-1;
    };
    int state_run=1;
    for(int i=(int)dg.size()-2;i>=0&&dg[i]->dom==dg.back()->dom;--i)++state_run;
    int curs=ps(dg.back()->dom),sign_run=1;
    int run_start=(int)dg.size()-1;
    while(run_start>0&&ps(dg[run_start-1]->dom)==curs){--run_start;++sign_run;}
    std::vector<int>runs,rsigns;
    int st=0;
    for(int i=1;i<=(int)dg.size();++i){
      if(i==(int)dg.size()||ps(dg[i]->dom)!=ps(dg[st]->dom)){
        runs.push_back(i-st);rsigns.push_back(ps(dg[st]->dom));st=i;
      }
    }
    int maxrun=*std::max_element(runs.begin(),runs.end());
    double meanrun=std::accumulate(runs.begin(),runs.end(),0.0)/runs.size();
    double persist=0;
    if(dg.size()>=2){
      int n=0;for(size_t i=1;i<dg.size();++i)if(ps(dg[i]->dom)==ps(dg[i-1]->dom))++n;
      persist=(double)n/(dg.size()-1);
    }
    int np=0;for(auto g:dg)if(ps(g->dom)>0)++np;
    double fracpos=(double)np/dg.size();
    double sr=0,total=0;
    for(size_t i=0;i<runs.size();++i){sr+=runs[i]*rsigns[i];total+=runs[i];}
    double since=32;
    if(run_start>0)since=clip((t-dg[run_start]->ts)/1e6,0,32);
    append(o,{(double)state_run,(double)sign_run,(double)maxrun,meanrun,persist,fracpos,ratio(sr,total),since});
  }

  // E2R09 G12 signed event-time momentum.
  std::array<double,4>mv{};
  const double hw[4]={1,4,16,32};
  auto esign=[](EC c){return (c==BI||c==BR||c==AD||c==AP)?1.0:-1.0;};
  for(int k=0;k<4;++k){
    double sn=0,ab=0;
    for(auto e:e32)if((t-e->ts)/1e6<=hw[k]){sn+=esign(e->cls)*e->absdq;ab+=e->absdq;}
    mv[k]=ratio(sn,ab);
  }
  std::vector<double>mx={0,2,4,5},my={mv[0],mv[1],mv[2],mv[3]};
  append(o,{mv[0],mv[1],mv[2],mv[3],mv[0]-mv[1],mv[1]-mv[2],mv[2]-mv[3],ols(mx,my)});

  // E2R10 I06 shock-conditioned recovery curve, latest shock per side.
  auto side_recovery=[&](bool bid){
    const DepthShock*sh=nullptr;
    for(auto it=dsh.rbegin();it!=dsh.rend();++it){
      if(t-it->ts>MAX_WINDOW_US)continue;
      if(it->bid==bid){sh=&*it;break;}
    }
    if(!sh)return std::array<double,6>{{0,0,0,0,0,32}};
    double age=clip((t-sh->ts)/1e6,0,32);
    auto depth_at=[&](double h){
      int64_t target=std::min<int64_t>(t,sh->ts+(int64_t)std::llround(h*1e6));
      double D=sh->d0;bool found=false;
      for(auto g:groups){
        if(!g.valid||g.ts<sh->ts||g.ts>target)continue;
        D=bid?sumq(g.post.bq,10):sumq(g.post.aq,10);found=true;
      }
      (void)found;
      return clip((D-sh->dmin)/std::max(sh->d0-sh->dmin,EPS),-1,2);
    };
    double r1=depth_at(1),r4=depth_at(4),r16=depth_at(16);
    double dc=bid?sumq(s.bq,10):sumq(s.aq,10);
    double rc=clip((dc-sh->dmin)/std::max(sh->d0-sh->dmin,EPS),-1,2);
    std::vector<double>x,y;
    for(double h:{1.0,4.0,16.0})if(h<=age+1e-12){x.push_back(h);y.push_back(h==1?r1:(h==4?r4:r16));}
    bool dup=false;for(double z:x)if(std::abs(z-age)<=1e-12)dup=true;
    if(!dup){x.push_back(age);y.push_back(rc);}
    else if(!x.empty())y.back()=rc;
    double sl=x.size()>=2?ols(x,y):0;
    return std::array<double,6>{{r1,r4,r16,rc,sl,age}};
  };
  auto br=side_recovery(true),ar=side_recovery(false);
  for(double x:br)append(o,{x});for(double x:ar)append(o,{x});

  return o;
}

void write_header(std::ofstream&o){
  o<<"local_timestamp_us,feature_valid";
  for(int ri=1;ri<=10;++ri){
    int n=COUNTS[ri-1];
    for(int j=0;j<n;++j)
      o<<",E2R"<<std::setw(2)<<std::setfill('0')<<ri<<"__f"<<std::setw(2)<<j;
  }
  o<<"\n";o<<std::setfill(' ');
}

void emit(std::ofstream&out,int64_t t,const Book&book,const std::deque<Ev>&evs,const std::deque<Group>&groups,
          const std::deque<DepthShock>&dsh,const std::deque<SpreadShock>&ssh,const std::deque<QueueShock>&qsh){
  Snapshot s=snap50(book);out<<t;
  if(!s.ok){out<<",0";for(int i=0;i<130;++i)out<<",nan";out<<"\n";return;}
  auto f=features(s,t,evs,groups,dsh,ssh,qsh);
  bool ok=f.size()==130;for(double x:f)ok=ok&&std::isfinite(x);
  if(!ok){out<<",0";for(int i=0;i<130;++i)out<<",nan";out<<"\n";return;}
  out<<",1"<<std::setprecision(17);for(double x:f)out<<','<<x;out<<"\n";
}

} // namespace

int main(int argc,char**argv){
  if(argc!=4){std::cerr<<"usage: dev032_e2a_raw_features INPUT.csv.gz SUPPORT.csv OUTPUT.csv\n";return 2;}
  auto support=read_support(argv[2]);std::ofstream out(argv[3]);if(!out)throw std::runtime_error("cannot open output");write_header(out);
  GzLineReader rd(argv[1]);std::string line;if(!rd.getline(line))throw std::runtime_error("missing header");
  if(line!="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount")throw std::runtime_error("unexpected raw header");

  Book book;std::vector<Row>grp;grp.reserve(4096);int64_t gts=std::numeric_limits<int64_t>::min();bool gsnap=false;
  std::deque<Ev>evs;std::deque<Group>groups;std::deque<DepthShock>dsh;std::deque<SpreadShock>ssh;std::deque<QueueShock>qsh;
  size_t si=0;uint64_t parsed=0,bad=0,emitted=0;int64_t prev=std::numeric_limits<int64_t>::min();

  auto trim=[&](int64_t t){
    while(!evs.empty()&&evs.front().ts<t-MAX_WINDOW_US)evs.pop_front();
    while(!groups.empty()&&groups.front().ts<t-MAX_WINDOW_US)groups.pop_front();
    while(!dsh.empty()&&dsh.front().ts<t-MAX_WINDOW_US)dsh.pop_front();
    while(!ssh.empty()&&ssh.front().ts<t-MAX_WINDOW_US)ssh.pop_front();
    while(!qsh.empty()&&qsh.front().ts<t-MAX_WINDOW_US)qsh.pop_front();
  };
  auto emit_before=[&](int64_t t){while(si<support.size()&&support[si]<t){trim(support[si]);emit(out,support[si],book,evs,groups,dsh,ssh,qsh);++si;++emitted;}};
  auto emit_equal=[&](int64_t t){while(si<support.size()&&support[si]==t){trim(t);emit(out,t,book,evs,groups,dsh,ssh,qsh);++si;++emitted;}};

  auto flush=[&](){
    if(grp.empty())return;
    emit_before(gts);
    Snapshot pre=snap50(book);bool eligible=pre.ok&&!gsnap;
    Group ga;ga.ts=gts;
    std::vector<Ev>new_events;

    if(gsnap)book.clear();

    for(const Row&r:grp){
      double old=book.qty(r.bid,r.price),nw=r.amount,dq=nw-old;
      if(eligible&&!r.snapshot&&dq!=0){
        EC c=NONE;
        if(old==0&&nw>0)c=r.bid?BI:AI;
        else if(old>0&&nw==0)c=r.bid?BD:AD;
        else if(old>0&&nw>old)c=r.bid?BR:AR;
        else if(old>nw&&nw>0)c=r.bid?BP:AP;
        if(c!=NONE){
          Ev e;e.ts=gts;e.cls=c;e.dq=dq;e.absdq=std::abs(dq);e.normden=std::max(old,nw);e.dist=10000*std::abs(r.price-pre.mid)/pre.mid;
          e.rank=insertion_rank(r.bid?pre.bp:pre.ap,r.price,r.bid);new_events.push_back(e);ga.counts[c]++;
          if(e.rank>0&&e.rank<=5&&(c==BD||c==BP||c==AD||c==AP)&&old>0&&(-dq)>=0.25*old){
            double D0=r.bid?sumq(pre.bq,10):sumq(pre.aq,10);dsh.push_back({gts,r.bid,D0,D0});
          }
        }
      }
      apply(book,r);
    }
    if(gsnap)book.ready=book.structurally_valid();else if(book.ready&&!book.structurally_valid())book.ready=false;

    Snapshot post=snap50(book);
    if(eligible&&post.ok){
      for(auto&e:new_events)evs.push_back(e);
      int best=-1;for(int i=0;i<8;++i)if(ga.counts[i]>best){best=ga.counts[i];ga.dom=(EC)i;}
      ga.has_dom=best>0;ga.valid=true;ga.post=post;ga.micro10=microdisp(post,10);ga.l1obi=imb(post.bq[0],post.aq[0]);groups.push_back(ga);

      for(auto&sh:dsh)if(gts-sh.ts<=US){double D=sh.bid?sumq(post.bq,10):sumq(post.aq,10);sh.dmin=std::min(sh.dmin,D);}
      if(pre.ok){
        if(post.spread_bps>=pre.spread_bps*1.25&&post.spread_bps-pre.spread_bps>=0.5)ssh.push_back({gts,pre.spread_bps,post.spread_bps});
        if(pre.bq[0]>0&&post.bq[0]<=0.75*pre.bq[0])qsh.push_back({gts,true,pre.bq[0],post.bq[0],post.bq[0]});
        if(pre.aq[0]>0&&post.aq[0]<=0.75*pre.aq[0])qsh.push_back({gts,false,pre.aq[0],post.aq[0],post.aq[0]});
      }
      for(auto&sh:qsh)if(gts-sh.ts<=US){double q=sh.bid?post.bq[0]:post.aq[0];sh.minpost=std::min(sh.minpost,q);}
    }
    trim(gts);emit_equal(gts);grp.clear();gsnap=false;
  };

  while(rd.getline(line)){
    ++parsed;Row r;if(!parse_row(line,r)){++bad;continue;}
    if(prev!=std::numeric_limits<int64_t>::min()&&r.local_ts<prev){std::cerr<<"timestamp regression\n";return 3;}prev=r.local_ts;
    if(gts==std::numeric_limits<int64_t>::min())gts=r.local_ts;
    if(r.local_ts!=gts){flush();gts=r.local_ts;}
    gsnap=gsnap||r.snapshot;grp.push_back(r);
  }
  flush();
  while(si<support.size()){trim(support[si]);emit(out,support[si],book,evs,groups,dsh,ssh,qsh);++si;++emitted;}
  std::cerr<<"parsed_rows="<<parsed<<" bad_rows="<<bad<<" support="<<support.size()<<" emitted="<<emitted<<"\n";
  if(bad||emitted!=support.size())return 4;
  return 0;
}
