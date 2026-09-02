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
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

constexpr int64_t US=1000000LL;
constexpr int64_t HISTORY_US=64LL*US;
constexpr double EPS=1e-12;

struct Row{
  int64_t exchange_ts=0,local_ts=0;
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
    return bids.begin()->first>0&&asks.begin()->first>bids.begin()->first;
  }
};

void apply(Book&b,const Row&r){
  if(r.bid){if(r.amount==0)b.bids.erase(r.price);else b.bids[r.price]=r.amount;}
  else{if(r.amount==0)b.asks.erase(r.price);else b.asks[r.price]=r.amount;}
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
    f_=gzopen(p.c_str(),"rb");if(!f_)throw std::runtime_error("cannot open gzip");
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
 private:
  gzFile*f_=nullptr;std::vector<char>buf_;
};

std::vector<int64_t> read_support(const std::string&p){
  std::ifstream in(p);if(!in)throw std::runtime_error("cannot open support");
  std::string line;
  if(!std::getline(in,line)||line!="local_timestamp_us")throw std::runtime_error("bad support header");
  std::vector<int64_t>x;
  while(std::getline(in,line))if(!line.empty())x.push_back(std::stoll(line));
  if(!std::is_sorted(x.begin(),x.end())||std::adjacent_find(x.begin(),x.end())!=x.end())
    throw std::runtime_error("support not unique sorted");
  return x;
}

struct Snapshot{
  std::array<double,50>bp{},bq{},ap{},aq{};
  bool ok=false;double mid=0,spread_bps=0;
};

Snapshot snap50(const Book&b){
  Snapshot s;
  if(!b.ready||!b.structurally_valid()||b.bids.size()<50||b.asks.size()<50)return s;
  int k=0;for(auto it=b.bids.begin();k<50;++it,++k){s.bp[k]=it->first;s.bq[k]=it->second;}
  k=0;for(auto it=b.asks.begin();k<50;++it,++k){s.ap[k]=it->first;s.aq[k]=it->second;}
  s.mid=(s.bp[0]+s.ap[0])/2.0;
  double spread=s.ap[0]-s.bp[0];
  s.spread_bps=10000.0*spread/s.mid;
  s.ok=std::isfinite(s.mid)&&s.mid>0&&spread>0;
  return s;
}

double sumq(const std::array<double,50>&q,int L){
  return std::accumulate(q.begin(),q.begin()+L,0.0);
}
double imb(double b,double a){double d=b+a;return d>0?(b-a)/d:0.0;}
double clip(double x,double lo,double hi){return std::max(lo,std::min(hi,x));}
double ols(const std::vector<double>&x,const std::vector<double>&y){
  if(x.size()!=y.size()||x.size()<2)return 0.0;
  double mx=std::accumulate(x.begin(),x.end(),0.0)/x.size();
  double my=std::accumulate(y.begin(),y.end(),0.0)/y.size();
  double num=0,den=0;
  for(size_t i=0;i<x.size();++i){double dx=x[i]-mx;num+=dx*(y[i]-my);den+=dx*dx;}
  return den>0?num/den:0.0;
}
int insertion_rank(const std::array<double,50>&p,double x,bool bid){
  for(int i=0;i<50;++i){
    if(x==p[i])return i+1;
    if(bid&&x>p[i])return i+1;
    if(!bid&&x<p[i])return i+1;
  }
  return 51;
}
double microdisp(const Snapshot&s,int L){
  double B=sumq(s.bq,L),A=sumq(s.aq,L),d=A+B;
  double m=d>0?(s.ap[0]*B+s.bp[0]*A)/d:s.mid;
  return 10000.0*(m-s.mid)/s.mid;
}
std::array<double,2> slopes10(const Snapshot&s){
  std::vector<double>bd,ad,by,ay;
  for(int i=0;i<10;++i){
    bd.push_back(10000*std::abs(s.bp[i]-s.mid)/s.mid);
    ad.push_back(10000*std::abs(s.ap[i]-s.mid)/s.mid);
    by.push_back(std::log1p(s.bq[i]));ay.push_back(std::log1p(s.aq[i]));
  }
  return {{ols(bd,by),ols(ad,ay)}};
}

enum EC{BI=0,BD=1,BR=2,BP=3,AI=4,AD=5,AR=6,AP=7,NONE=8};
const std::array<std::string,8> ECN={{"BI","BD","BR","BP","AI","AD","AR","AP"}};

struct Ev{int64_t ts=0;EC cls=NONE;double dq=0,absdq=0;int rank=0;};
struct StatePoint{int64_t ts=0;Snapshot s;};
struct DepthShock{int64_t ts=0;bool bid=false;double d0=0;};
struct SpreadShock{int64_t ts=0;double pre=0,shock=0;};

const Snapshot* state_at(const std::deque<StatePoint>&states,int64_t endpoint){
  for(auto it=states.rbegin();it!=states.rend();++it)if(it->ts<=endpoint)return &it->s;
  return nullptr;
}

std::vector<const Ev*> bin_events(const std::deque<Ev>&evs,int64_t t,int k){
  int64_t hi=t-(int64_t)k*US;
  int64_t lo=t-(int64_t)(k+1)*US;
  std::vector<const Ev*> out;
  for(const auto&e:evs)if(e.ts>lo&&e.ts<=hi)out.push_back(&e);
  return out;
}

std::array<double,6> geometry(const Snapshot&s){
  auto sl=slopes10(s);
  double bnf=sumq(s.bq,10)/std::max(sumq(s.bq,50),EPS);
  double anf=sumq(s.aq,10)/std::max(sumq(s.aq,50),EPS);
  double bg=0,ag=0;
  for(int i=0;i<9;++i){
    bg+=10000.0*(s.bp[i]-s.bp[i+1])/s.mid;
    ag+=10000.0*(s.ap[i+1]-s.ap[i])/s.mid;
  }
  return {{sl[0],sl[1],sl[0]-sl[1],bnf-anf,bg/9.0,ag/9.0}};
}

double depth_recovery(
  bool bid,int64_t endpoint,const Snapshot&current,
  const std::deque<DepthShock>&shocks,const std::deque<StatePoint>&states
){
  const DepthShock* sh=nullptr;
  for(auto it=shocks.rbegin();it!=shocks.rend();++it){
    if(it->ts<=endpoint&&endpoint-it->ts<=32LL*US&&it->bid==bid){sh=&*it;break;}
  }
  if(!sh)return 0.0;
  double dmin=sh->d0;
  int64_t until=std::min(endpoint,sh->ts+US);
  for(const auto&sp:states){
    if(sp.ts<sh->ts||sp.ts>until)continue;
    double d=bid?sumq(sp.s.bq,10):sumq(sp.s.aq,10);
    dmin=std::min(dmin,d);
  }
  double dt=bid?sumq(current.bq,10):sumq(current.aq,10);
  return clip((dt-dmin)/std::max(sh->d0-dmin,EPS),-1,2);
}

double spread_recovery(
  int64_t endpoint,const Snapshot&current,
  const std::deque<SpreadShock>&shocks
){
  const SpreadShock*sh=nullptr;
  for(auto it=shocks.rbegin();it!=shocks.rend();++it){
    if(it->ts<=endpoint&&endpoint-it->ts<=32LL*US){sh=&*it;break;}
  }
  if(!sh)return 0.0;
  return clip((sh->shock-current.spread_bps)/std::max(sh->shock-sh->pre,EPS),-1,2);
}

std::vector<double> family_at(
  int family,int window,int64_t t,
  const std::deque<StatePoint>&states,const std::deque<Ev>&evs,
  const std::deque<DepthShock>&dsh,const std::deque<SpreadShock>&ssh,
  bool&ok
){
  std::vector<double> out;
  ok=true;
  for(int k=0;k<window;++k){
    int64_t endpoint=t-(int64_t)k*US;
    if(family==4||family==5||family==6){
      auto es=bin_events(evs,t,k);
      if(family==4){
        std::array<double,10>num{},den{};
        for(auto e:es)if(e->rank>=1&&e->rank<=10){
          int j=e->rank-1;double sign=e->cls<AI?1.0:-1.0;
          num[j]+=sign*e->dq;den[j]+=e->absdq;
        }
        for(int j=0;j<10;++j)out.push_back(den[j]>0?num[j]/den[j]:0.0);
      }else if(family==5){
        std::array<double,8>q{};double den=0;
        for(auto e:es){q[e->cls]+=e->absdq;den+=e->absdq;}
        for(double z:q)out.push_back(den>0?z/den:0.0);
      }else{
        std::array<double,8>c{};double den=0;
        for(auto e:es){c[e->cls]+=1.0;den+=1.0;}
        for(double z:c)out.push_back(den>0?z/den:0.0);
      }
      continue;
    }

    const Snapshot*s=state_at(states,endpoint);
    if(!s||!s->ok){ok=false;return {};}

    if(family==1){
      out.push_back(imb(s->bq[0],s->aq[0]));
    }else if(family==2){
      for(int L:{1,5,10,20})out.push_back(imb(sumq(s->bq,L),sumq(s->aq,L)));
    }else if(family==3){
      for(int L:{1,5,10,20})out.push_back(microdisp(*s,L));
    }else if(family==7){
      auto g=geometry(*s);for(double z:g)out.push_back(z);
    }else if(family==8){
      double br=depth_recovery(true,endpoint,*s,dsh,states);
      double ar=depth_recovery(false,endpoint,*s,dsh,states);
      double sr=spread_recovery(endpoint,*s,ssh);
      out.push_back(br);out.push_back(ar);out.push_back(br-ar);out.push_back(sr);
    }else{
      ok=false;return {};
    }
  }
  for(double z:out)if(!std::isfinite(z)){ok=false;return {};}
  return out;
}

int channels(int family){
  const int c[8]={1,4,4,10,8,8,6,4};
  return c[family-1];
}

void feature_names(int cid,int family,int window,std::vector<std::string>&out){
  static const std::vector<std::vector<std::string>> names={
    {"l1_queue_imbalance"},
    {"depth_imbalance_l1","depth_imbalance_l5","depth_imbalance_l10","depth_imbalance_l20"},
    {"microdisp_l1_bps","microdisp_l5_bps","microdisp_l10_bps","microdisp_l20_bps"},
    {"mlofi_rank_01","mlofi_rank_02","mlofi_rank_03","mlofi_rank_04","mlofi_rank_05","mlofi_rank_06","mlofi_rank_07","mlofi_rank_08","mlofi_rank_09","mlofi_rank_10"},
    {"qtyshare_BI","qtyshare_BD","qtyshare_BR","qtyshare_BP","qtyshare_AI","qtyshare_AD","qtyshare_AR","qtyshare_AP"},
    {"countshare_BI","countshare_BD","countshare_BR","countshare_BP","countshare_AI","countshare_AD","countshare_AR","countshare_AP"},
    {"bid_slope_l10","ask_slope_l10","slope_diff_l10","near_far_depth_diff","mean_bid_gap_l10","mean_ask_gap_l10"},
    {"bid_depth_recovery","ask_depth_recovery","depth_recovery_diff","spread_recovery"}
  };
  std::string p="G2C"+std::string(cid<10?"0":"")+std::to_string(cid);
  for(int k=0;k<window;++k)
    for(const auto&n:names[family-1])
      out.push_back(p+"__bin"+std::string(k<10?"0":"")+std::to_string(k)+"__"+n);
}

void write_header(std::ofstream&out){
  out<<"local_timestamp_us,feature_valid";
  int cid=0;
  for(int window:{8,16,32})for(int family=1;family<=8;++family){
    ++cid;std::vector<std::string>n;feature_names(cid,family,window,n);
    for(const auto&s:n)out<<','<<s;
  }
  out<<"\n";
}

void emit(
  std::ofstream&out,int64_t t,
  const std::deque<StatePoint>&states,const std::deque<Ev>&evs,
  const std::deque<DepthShock>&dsh,const std::deque<SpreadShock>&ssh
){
  std::vector<double> all;all.reserve(2520);bool valid=true;
  for(int window:{8,16,32})for(int family=1;family<=8;++family){
    bool ok=false;auto z=family_at(family,window,t,states,evs,dsh,ssh,ok);
    if(!ok||z.size()!=(size_t)(window*channels(family))){valid=false;break;}
    all.insert(all.end(),z.begin(),z.end());
  }
  out<<t;
  if(!valid||all.size()!=2520){
    out<<",0";for(int i=0;i<2520;++i)out<<",nan";out<<"\n";return;
  }
  out<<",1"<<std::setprecision(17);
  for(double z:all)out<<','<<z;
  out<<"\n";
}

} // namespace

int main(int argc,char**argv){
  if(argc!=4){
    std::cerr<<"usage: dev033_g2a_raw_temporal INPUT.csv.gz SUPPORT.csv OUTPUT.csv\n";
    return 2;
  }
  auto support=read_support(argv[2]);
  std::ofstream out(argv[3]);if(!out)throw std::runtime_error("cannot open output");
  write_header(out);

  GzLineReader rd(argv[1]);std::string line;
  if(!rd.getline(line))throw std::runtime_error("missing header");
  if(line!="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount")
    throw std::runtime_error("unexpected raw header");

  Book book;
  std::vector<Row>grp;grp.reserve(4096);
  int64_t gts=std::numeric_limits<int64_t>::min(),prev=std::numeric_limits<int64_t>::min();
  bool gsnap=false;
  std::deque<StatePoint>states;
  std::deque<Ev>evs;
  std::deque<DepthShock>dsh;
  std::deque<SpreadShock>ssh;
  size_t si=0;uint64_t parsed=0,bad=0,emitted=0;

  auto trim=[&](int64_t t){
    while(!states.empty()&&states.front().ts<t-HISTORY_US)states.pop_front();
    while(!evs.empty()&&evs.front().ts<t-HISTORY_US)evs.pop_front();
    while(!dsh.empty()&&dsh.front().ts<t-HISTORY_US)dsh.pop_front();
    while(!ssh.empty()&&ssh.front().ts<t-HISTORY_US)ssh.pop_front();
  };

  auto emit_before=[&](int64_t t){
    while(si<support.size()&&support[si]<t){
      trim(support[si]);emit(out,support[si],states,evs,dsh,ssh);++si;++emitted;
    }
  };
  auto emit_equal=[&](int64_t t){
    while(si<support.size()&&support[si]==t){
      trim(t);emit(out,t,states,evs,dsh,ssh);++si;++emitted;
    }
  };

  auto flush=[&](){
    if(grp.empty())return;
    emit_before(gts);
    Snapshot pre=snap50(book);
    bool eligible=pre.ok&&!gsnap;
    std::vector<Ev>new_events;
    std::vector<DepthShock>new_dsh;

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
          Ev e;e.ts=gts;e.cls=c;e.dq=dq;e.absdq=std::abs(dq);
          e.rank=insertion_rank(r.bid?pre.bp:pre.ap,r.price,r.bid);
          new_events.push_back(e);
          if(e.rank>=1&&e.rank<=5&&(c==BD||c==BP||c==AD||c==AP)&&old>0&&(-dq)>=0.25*old){
            double d0=r.bid?sumq(pre.bq,10):sumq(pre.aq,10);
            new_dsh.push_back({gts,r.bid,d0});
          }
        }
      }
      apply(book,r);
    }

    if(gsnap)book.ready=book.structurally_valid();
    else if(book.ready&&!book.structurally_valid())book.ready=false;

    Snapshot post=snap50(book);
    if(post.ok){
      states.push_back({gts,post});
      if(eligible){
        for(const auto&e:new_events)evs.push_back(e);
        for(const auto&s:new_dsh)dsh.push_back(s);
        if(pre.ok&&post.spread_bps>=pre.spread_bps*1.25&&post.spread_bps-pre.spread_bps>=0.5)
          ssh.push_back({gts,pre.spread_bps,post.spread_bps});
      }
    }

    trim(gts);
    emit_equal(gts);
    grp.clear();gsnap=false;
  };

  while(rd.getline(line)){
    ++parsed;Row r;
    if(!parse_row(line,r)){++bad;continue;}
    if(prev!=std::numeric_limits<int64_t>::min()&&r.local_ts<prev){
      std::cerr<<"timestamp regression\n";return 3;
    }
    prev=r.local_ts;
    if(gts==std::numeric_limits<int64_t>::min())gts=r.local_ts;
    if(r.local_ts!=gts){flush();gts=r.local_ts;}
    gsnap=gsnap||r.snapshot;grp.push_back(r);
  }
  flush();

  while(si<support.size()){
    trim(support[si]);emit(out,support[si],states,evs,dsh,ssh);++si;++emitted;
  }

  std::cerr<<"parsed_rows="<<parsed<<" bad_rows="<<bad
           <<" support="<<support.size()<<" emitted="<<emitted<<"\n";
  if(bad||emitted!=support.size())return 4;
  return 0;
}
