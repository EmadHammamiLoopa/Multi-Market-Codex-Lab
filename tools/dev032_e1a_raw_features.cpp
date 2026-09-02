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

const std::array<int,32> COUNTS={{
  1,7,2,7,5,5,4,10,20,4,10,40,2,2,4,4,6,8,6,4,16,12,8,8,8,16,6,6,4,4,15,24
}};

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
int rank_price(const std::array<double,50>&p,double x){
  for(int i=0;i<50;++i)if(p[i]==x)return i+1;
  return 0;
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
  int64_t ts=0;EC cls=NONE;double dq=0,absdq=0,dist=0;int rank=0;
};
struct Group{
  int64_t ts=0;std::array<int,8>counts{};bool has_dom=false;EC dom=NONE;
  double micro10=0;Snapshot post;bool valid=false;
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
  std::vector<double>o;o.reserve(278);
  if(!s.ok)return o;

  // S04
  append(o,{imb(s.bq[0],s.aq[0])});

  // S05
  const int Ls[7]={1,2,3,5,10,20,50};
  for(int L:Ls)append(o,{imb(sumq(s.bq,L),sumq(s.aq,L))});

  // S06
  double ib=0,ia=0,eb=0,ea=0;
  for(int i=0;i<50;++i){
    double bd=10000*std::abs(s.bp[i]-s.mid)/s.mid,ad=10000*std::abs(s.ap[i]-s.mid)/s.mid;
    ib+=s.bq[i]/(1+bd);ia+=s.aq[i]/(1+ad);eb+=s.bq[i]*std::exp(-bd/10);ea+=s.aq[i]*std::exp(-ad/10);
  }
  append(o,{imb(ib,ia),imb(eb,ea)});

  // S07
  for(int L:Ls)append(o,{std::log((sumq(s.bq,L)+EPS)/(sumq(s.aq,L)+EPS))});

  // S08/S09
  std::array<double,5> md{};int ML[5]={1,5,10,20,50};
  for(int j=0;j<5;++j){md[j]=microdisp(s,ML[j]);append(o,{md[j]});}
  for(double x:md)append(o,{s.spread_bps>0?x/s.spread_bps:0});

  // S10
  auto gs=groups_in(groups,t);
  std::vector<double>tx,vy;for(auto g:gs){tx.push_back((g->ts-(gs.empty()?t:gs.front()->ts))/1e6);vy.push_back(g->micro10);}
  double vel=0,sl=0,m4=0,m32=0,m1=0,m16=0;int n4=0,n32=0,n1=0,n16=0;
  if(vy.size()>=2){double elapsed=tx.back()-tx.front();vel=elapsed>0?(vy.back()-vy.front())/elapsed:0;sl=ols(tx,vy);}
  for(auto g:gs){double age=(t-g->ts)/1e6;m32+=g->micro10;++n32;if(age<=16){m16+=g->micro10;++n16;}if(age<=4){m4+=g->micro10;++n4;}if(age<=1){m1+=g->micro10;++n1;}}
  append(o,{vel,sl,(n4?m4/n4:0)-(n32?m32/n32:0),(n1?m1/n1:0)-(n16?m16/n16:0)});

  auto e32=events_in(evs,t,0,32);

  // S11/S12
  for(int top:{10,20}){
    for(int j=1;j<=top;++j){double sn=0,ab=0;for(auto e:e32)if(e->rank==j){sn+=(e->cls<AI?1:-1)*e->dq;ab+=e->absdq;}append(o,{ratio(sn,ab)});}
  }

  // S13 disjoint distance buckets
  for(int b=0;b<4;++b){double sn=0,ab=0;for(auto e:e32){
    bool in=(b==0?e->dist<=5:b==1?(e->dist>5&&e->dist<=15):b==2?(e->dist>15&&e->dist<=50):e->dist>50);
    if(in){sn+=(e->cls<AI?1:-1)*e->dq;ab+=e->absdq;}
  }append(o,{ratio(sn,ab)});}

  // S14 normalized top10 flow means
  for(int j=1;j<=10;++j){double z=0;int n=0;for(auto e:e32)if(e->rank==j){
    double den=std::max(e->absdq,EPS);double signed_norm=(e->cls<AI?1:-1)*e->dq/den;z+=signed_norm;++n;
  }append(o,{n?z/n:0});}

  // S15 top10 signed totals 1/4/16/32
  for(double w:{1.0,4.0,16.0,32.0})for(int j=1;j<=10;++j){double sn=0;for(auto e:e32)if((t-e->ts)/1e6<=w&&e->rank==j)sn+=(e->cls<AI?1:-1)*e->dq;append(o,{sn});}

  // S16/S17
  auto s10=slopes(s,10),s20=slopes(s,20),s50=slopes(s,50);
  append(o,{s10[0],s10[1],s50[0],s50[1]});

  // S18
  append(o,{s20[0]-s20[1],s50[0]-s50[1],ratio(sumq(s.bq,10),sumq(s.bq,50)),ratio(sumq(s.aq,10),sumq(s.aq,50))});

  // S19
  auto gap=[&](bool bid,int i){double x=bid?s.bp[i]-s.bp[i+1]:s.ap[i+1]-s.ap[i];return 10000*x/s.mid;};
  double mb10=0,ma10=0,mb50=0,ma50=0;for(int i=0;i<49;++i){double gb=gap(true,i),ga=gap(false,i);mb50+=gb;ma50+=ga;if(i<9){mb10+=gb;ma10+=ga;}}
  append(o,{gap(true,0)-gap(false,0),gap(true,1)-gap(false,1),mb10/9-ma10/9,mb50/49-ma50/49});

  // S20
  double sb=sumq(s.bq,50),sa=sumq(s.aq,50),cb=0,ca=0,hb=0,ha=0;
  for(int i=0;i<50;++i){
    double wb=s.bq[i]/std::max(sb,EPS),wa=s.aq[i]/std::max(sa,EPS);
    double db=10000*std::abs(s.bp[i]-s.mid)/s.mid,da=10000*std::abs(s.ap[i]-s.mid)/s.mid;
    cb+=wb*db;ca+=wa*da;if(wb>0)hb-=wb*std::log(wb);if(wa>0)ha-=wa*std::log(wa);
  }hb/=std::log(50.0);ha/=std::log(50.0);
  append(o,{cb,ca,ca-cb,hb,ha,hb-ha});

  // S21
  for(int type=0;type<4;++type)for(int region=0;region<2;++region){
    double nb=0,na=0;for(auto e:e32){bool near=e->dist<=5,deep=e->dist>5&&e->dist<=50;if((region==0&&!near)||(region==1&&!deep))continue;
      if(e->cls==type)++nb;if(e->cls==type+4)++na;
    }
    append(o,{(type==1||type==3)?imb(na,nb):imb(nb,na)});
  }

  // counts by class
  std::array<double,8>cnt{};std::array<double,8>qty{};
  for(auto e:e32){cnt[e->cls]+=1;qty[e->cls]+=e->absdq;}

  // S22
  double bca=ratio(cnt[BD],cnt[BI]+cnt[BD]),aca=ratio(cnt[AD],cnt[AI]+cnt[AD]);
  double brd=ratio(cnt[BR],cnt[BR]+cnt[BP]),ard=ratio(cnt[AR],cnt[AR]+cnt[AP]);
  append(o,{bca,aca,brd,ard,bca-aca,brd-ard});

  // S23
  double bid_signed=0,ask_signed=0,bcreate=0,acreate=0,bdestroy=0,adestroy=0;
  for(auto e:e32){
    bool bid=e->cls<AI;
    if(bid){bid_signed+=e->dq;if(e->dq>0)bcreate+=e->dq;else bdestroy+=-e->dq;}
    else{ask_signed+=e->dq;if(e->dq>0)acreate+=e->dq;else adestroy+=-e->dq;}
  }
  double bidabs=bcreate+bdestroy,askabs=acreate+adestroy;
  append(o,{ratio(bid_signed,bidabs),ratio(ask_signed,askabs),imb(bcreate,acreate),imb(adestroy,bdestroy)});

  // S24 dominant-group transitions
  std::array<std::array<double,8>,8>tr{};
  std::vector<EC>dom;for(auto g:gs)if(g->has_dom)dom.push_back(g->dom);
  for(size_t i=1;i<dom.size();++i)tr[dom[i-1]][dom[i]]++;
  for(int i=0;i<8;++i){double den=0;for(double x:tr[i])den+=x;if(den<=0){append(o,{0,0});continue;}
    double bid=0,ask=0,add=0,rem=0;for(int j=0;j<8;++j){double p=tr[i][j]/den;(j<4?bid:ask)+=p;((j%4==0||j%4==2)?add:rem)+=p;}append(o,{bid-ask,add-rem});
  }

  // helper class times in seconds from window start for four classes
  std::array<std::vector<double>,4>ct;
  for(auto e:e32){int c=-1;if(e->cls==BI||e->cls==BR)c=0;else if(e->cls==BD||e->cls==BP)c=1;else if(e->cls==AI||e->cls==AR)c=2;else c=3;ct[c].push_back((e->ts-(t-MAX_WINDOW_US))/1e6);}
  // S25
  for(auto v:ct){std::sort(v.begin(),v.end());if(v.size()<2){append(o,{32,0,0});continue;}std::vector<double>d;for(size_t i=1;i<v.size();++i)d.push_back(v[i]-v[i-1]);
    double m=std::accumulate(d.begin(),d.end(),0.0)/d.size(),ss=0;for(double x:d)ss+=(x-m)*(x-m);double sd=std::sqrt(ss/d.size());append(o,{m,sd,m>0?sd/m:0});
  }
  // S26
  for(auto v:ct){std::sort(v.begin(),v.end());double mean=32,sd=0;if(v.size()>=2){std::vector<double>d;for(size_t i=1;i<v.size();++i)d.push_back(v[i]-v[i-1]);mean=std::accumulate(d.begin(),d.end(),0.0)/d.size();double ss=0;for(double x:d)ss+=(x-mean)*(x-mean);sd=std::sqrt(ss/d.size());}
    double B=(mean+sd)>0?(sd-mean)/(sd+mean):0;std::array<double,8>bins{};for(double x:v){int bi=std::min(7,std::max(0,(int)std::floor(x/4)));bins[bi]++;}double bm=std::accumulate(bins.begin(),bins.end(),0.0)/8,vs=0;for(double x:bins)vs+=(x-bm)*(x-bm);double fano=bm>0?(vs/8)/bm:0;append(o,{B,fano});
  }
  // S27
  for(int c=0;c<4;++c){auto countw=[&](double w){int n=0;for(double x:ct[c])if(x>=32-w)++n;return (double)n;};double i1=countw(1),i4=countw(4)/4,i16=countw(16)/16,i32=countw(32)/32;append(o,{clip(i1/(i16+EPS),0,32),clip(i4/(i32+EPS),0,32)});}
  // S28
  for(int c=0;c<8;++c){double age=32;for(auto e:e32)if(e->cls==c)age=std::min(age,(t-e->ts)/1e6);append(o,{age});}
  // S29
  std::array<double,8>i1{},i8{};for(int c=0;c<8;++c){i1[c]=expint(evs,t,(EC)c,1);i8[c]=expint(evs,t,(EC)c,8);append(o,{i1[c],i8[c]});}
  // S30
  double ba1=i1[BI]+i1[BR],aa1=i1[AI]+i1[AR],ba8=i8[BI]+i8[BR],aa8=i8[AI]+i8[AR];
  append(o,{imb(ba1,aa1),imb(ba8,aa8),clip(ba1/(ba8+EPS),0,32),clip(aa1/(aa8+EPS),0,32),(ba1-aa1)-(ba8-aa8),clip((ba1+aa1)/(ba8+aa8+EPS),0,32)});
  // S31
  double br1=i1[BD]+i1[BP],ar1=i1[AD]+i1[AP],br8=i8[BD]+i8[BP],ar8=i8[AD]+i8[AP];
  append(o,{imb(ar1,br1),imb(ar8,br8),clip(br1/(br8+EPS),0,32),clip(ar1/(ar8+EPS),0,32),(ar1-br1)-(ar8-br8),clip((br1+ar1)/(br8+ar8+EPS),0,32)});

  // S32 latest shock each side
  for(bool bid:{true,false}){double rec=0,age=32;for(auto it=dsh.rbegin();it!=dsh.rend();++it)if(it->bid==bid&&t-it->ts<=MAX_WINDOW_US){double Dt=bid?sumq(s.bq,10):sumq(s.aq,10);rec=clip((Dt-it->dmin)/std::max(it->d0-it->dmin,EPS),-1,2);age=(t-it->ts)/1e6;break;}append(o,{rec,age});}

  // S33 spread recovery + bid/ask queue refill
  double sr=0,sage=32;for(auto it=ssh.rbegin();it!=ssh.rend();++it)if(t-it->ts<=MAX_WINDOW_US){sr=clip((it->shock-s.spread_bps)/std::max(it->shock-it->pre,EPS),-1,2);sage=(t-it->ts)/1e6;break;}
  double bqr=0,aqr=0;for(auto it=qsh.rbegin();it!=qsh.rend();++it)if(t-it->ts<=MAX_WINDOW_US){double cur=it->bid?s.bq[0]:s.aq[0];double rr=clip((cur-it->minpost)/std::max(it->pre-it->minpost,EPS),-1,2);if(it->bid&&bqr==0)bqr=rr;if(!it->bid&&aqr==0)aqr=rr;}
  append(o,{sr,sage,bqr,aqr});

  // S34 four disjoint bands, normalized top10 vectors
  std::array<std::array<double,10>,4>vec{};
  for(int b=0;b<4;++b){double lo=b==0?0:b==1?1:b==2?4:16,hi=b==0?1:b==1?4:b==2?16:32,abs=0;for(auto e:e32){double age=(t-e->ts)/1e6;if(age>lo&&age<=hi&&e->rank>=1&&e->rank<=10){double sn=(e->cls<AI?1:-1)*e->dq;vec[b][e->rank-1]+=sn;abs+=e->absdq;}}if(abs>0)for(double&x:vec[b])x/=abs;}
  for(int b=0;b<4;++b){double z=std::accumulate(vec[b].begin(),vec[b].end(),0.0);append(o,{z});}
  for(int b=0;b<4;++b){double z=0;for(double x:vec[b])z+=std::abs(x);append(o,{z});}
  append(o,{cosine(vec[0],vec[1]),cosine(vec[1],vec[2]),cosine(vec[2],vec[3])});
  for(int b=0;b<4;++b){double near=vec[b][0]+vec[b][1]+vec[b][2],deep=vec[b][7]+vec[b][8]+vec[b][9];append(o,{near-deep});}

  // S35 4 bands x 4 event-type pressure, then short-long and OLS slope
  std::array<std::array<double,4>,4>pr{};
  for(int b=0;b<4;++b){double lo=b==0?0:b==1?1:b==2?4:16,hi=b==0?1:b==1?4:b==2?16:32;for(int typ=0;typ<4;++typ){double nb=0,na=0;for(auto e:e32){double age=(t-e->ts)/1e6;if(!(age>lo&&age<=hi))continue;if(e->cls==typ)++nb;if(e->cls==typ+4)++na;}pr[b][typ]=(typ==1||typ==3)?imb(na,nb):imb(nb,na);append(o,{pr[b][typ]});}}
  std::vector<double>mids={0.5,2.5,10,24};for(int typ=0;typ<4;++typ){std::vector<double>y;for(int b=0;b<4;++b)y.push_back(pr[b][typ]);append(o,{pr[0][typ]-pr[3][typ],ols(mids,y)});}

  return o;
}

void write_header(std::ofstream&o){
  o<<"local_timestamp_us,feature_valid";
  for(int si=4;si<36;++si){int n=COUNTS[si-4];for(int j=0;j<n;++j)o<<",S"<<std::setw(2)<<std::setfill('0')<<si<<"__f"<<std::setw(2)<<j;}
  o<<"\n";o<<std::setfill(' ');
}

void emit(std::ofstream&out,int64_t t,const Book&book,const std::deque<Ev>&evs,const std::deque<Group>&groups,
          const std::deque<DepthShock>&dsh,const std::deque<SpreadShock>&ssh,const std::deque<QueueShock>&qsh){
  Snapshot s=snap50(book);out<<t;
  if(!s.ok){out<<",0";for(int i=0;i<278;++i)out<<",nan";out<<"\n";return;}
  auto f=features(s,t,evs,groups,dsh,ssh,qsh);
  bool ok=f.size()==278;for(double x:f)ok=ok&&std::isfinite(x);
  if(!ok){out<<",0";for(int i=0;i<278;++i)out<<",nan";out<<"\n";return;}
  out<<",1"<<std::setprecision(17);for(double x:f)out<<','<<x;out<<"\n";
}

} // namespace

int main(int argc,char**argv){
  if(argc!=4){std::cerr<<"usage: dev032_e1a_raw_features INPUT.csv.gz SUPPORT.csv OUTPUT.csv\n";return 2;}
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
          Ev e;e.ts=gts;e.cls=c;e.dq=dq;e.absdq=std::abs(dq);e.dist=10000*std::abs(r.price-pre.mid)/pre.mid;
          e.rank=rank_price(r.bid?pre.bp:pre.ap,r.price);new_events.push_back(e);ga.counts[c]++;
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
      ga.has_dom=best>0;ga.valid=true;ga.post=post;ga.micro10=microdisp(post,10);groups.push_back(ga);

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
