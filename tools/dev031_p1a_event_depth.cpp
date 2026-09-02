#include <zlib.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <deque>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

constexpr int64_t US = 1000000LL;
constexpr int64_t MAX_WINDOW_US = 32LL * US;

struct Row {
  int64_t exchange_ts = 0;
  int64_t local_ts = 0;
  bool snapshot = false;
  bool bid = false;
  double price = 0.0;
  double amount = 0.0;
};

struct Book {
  std::map<double,double,std::greater<double>> bids;
  std::map<double,double> asks;
  bool ready = false;

  void clear() { bids.clear(); asks.clear(); ready = false; }

  double qty(bool bid, double price) const {
    if (bid) {
      const auto it = bids.find(price);
      return it == bids.end() ? 0.0 : it->second;
    }
    const auto it = asks.find(price);
    return it == asks.end() ? 0.0 : it->second;
  }

  void apply(const Row& r) {
    auto& side = r.bid ? bids : asks;
    if (r.amount == 0.0) side.erase(r.price);
    else side[r.price] = r.amount;
  }

  bool structurally_valid() const {
    if (bids.empty() || asks.empty()) return false;
    const double b = bids.begin()->first;
    const double a = asks.begin()->first;
    return std::isfinite(b) && std::isfinite(a) && b > 0.0 && a > b;
  }

  bool valid() const { return ready && structurally_valid(); }

  double mid() const {
    if (!valid()) return std::numeric_limits<double>::quiet_NaN();
    return (bids.begin()->first + asks.begin()->first) / 2.0;
  }
};

struct GroupAgg {
  int64_t ts = 0;
  std::array<double,3> signed_flow{{0,0,0}};
  std::array<double,3> abs_flow{{0,0,0}};
  uint64_t bid_insert=0, ask_insert=0;
  uint64_t bid_delete=0, ask_delete=0;
  uint64_t bid_replenish=0, ask_replenish=0;
  uint64_t bid_deplete=0, ask_deplete=0;
  uint64_t updates=0;
  bool eligible=false;
};

bool parse_bool(const char* s, size_t n) {
  return n == 4 && (s[0]=='t' || s[0]=='T');
}

bool parse_row(const std::string& line, Row& out) {
  std::array<std::pair<const char*,size_t>,8> f{};
  size_t field=0,start=0;
  for (size_t i=0;i<=line.size();++i) {
    if (i==line.size() || line[i]==',') {
      if (field>=f.size()) return false;
      f[field++]={line.data()+start,i-start};
      start=i+1;
    }
  }
  if (field!=8) return false;
  try {
    out.exchange_ts=std::stoll(std::string(f[2].first,f[2].second));
    out.local_ts=std::stoll(std::string(f[3].first,f[3].second));
    out.snapshot=parse_bool(f[4].first,f[4].second);
    const std::string side(f[5].first,f[5].second);
    if (side=="bid") out.bid=true;
    else if (side=="ask") out.bid=false;
    else return false;
    out.price=std::stod(std::string(f[6].first,f[6].second));
    out.amount=std::stod(std::string(f[7].first,f[7].second));
  } catch (...) { return false; }
  return std::isfinite(out.price) && out.price>0.0 &&
         std::isfinite(out.amount) && out.amount>=0.0;
}

class GzLineReader {
 public:
  explicit GzLineReader(const std::string& path) {
    f_=gzopen(path.c_str(),"rb");
    if(!f_) throw std::runtime_error("cannot open gzip input: "+path);
    buf_.resize(1<<20);
  }
  ~GzLineReader(){ if(f_) gzclose(f_); }
  bool getline(std::string& out){
    out.clear();
    while(true){
      char* p=gzgets(f_,buf_.data(),static_cast<int>(buf_.size()));
      if(!p) return !out.empty();
      size_t n=std::char_traits<char>::length(p);
      out.append(p,n);
      if(n && p[n-1]=='\n'){
        while(!out.empty() && (out.back()=='\n'||out.back()=='\r')) out.pop_back();
        return true;
      }
      if(gzeof(f_)) return !out.empty();
    }
  }
 private:
  gzFile f_=nullptr;
  std::vector<char> buf_;
};

std::vector<int64_t> read_support(const std::string& path) {
  std::ifstream in(path);
  if(!in) throw std::runtime_error("cannot open support file");
  std::string line;
  if(!std::getline(in,line) || line!="local_timestamp_us") {
    throw std::runtime_error("unexpected support header");
  }
  std::vector<int64_t> out;
  while(std::getline(in,line)) {
    if(line.empty()) continue;
    out.push_back(std::stoll(line));
  }
  if(!std::is_sorted(out.begin(),out.end())) throw std::runtime_error("support not sorted");
  if(std::adjacent_find(out.begin(),out.end())!=out.end()) throw std::runtime_error("support duplicate");
  return out;
}

double imbalance(double b,double a){
  const double d=b+a;
  return d>0.0 ? (b-a)/d : 0.0;
}

double safe_ratio(double n,double d){ return d>0.0 ? n/d : 0.0; }

void top_depth(const Book& b, double& bid10, double& ask10,
               double& bid20, double& ask20, double& bid50, double& ask50) {
  bid10=ask10=bid20=ask20=bid50=ask50=0.0;
  int k=0;
  for(auto it=b.bids.begin();it!=b.bids.end() && k<50;++it,++k){
    if(k<10) bid10+=it->second;
    if(k<20) bid20+=it->second;
    bid50+=it->second;
  }
  k=0;
  for(auto it=b.asks.begin();it!=b.asks.end() && k<50;++it,++k){
    if(k<10) ask10+=it->second;
    if(k<20) ask20+=it->second;
    ask50+=it->second;
  }
}

void write_header(std::ofstream& o){
  o<<"local_timestamp_us,feature_valid"
   <<",obi_l20,obi_l50"
   <<",log1p_bid_depth_l20,log1p_ask_depth_l20"
   <<",log1p_bid_depth_l50,log1p_ask_depth_l50"
   <<",bid_depth_concentration_l10_l50,ask_depth_concentration_l10_l50"
   <<",flow_imbalance_1s_5bp,flow_imbalance_1s_15bp,flow_imbalance_1s_50bp"
   <<",flow_imbalance_4s_5bp,flow_imbalance_4s_15bp,flow_imbalance_4s_50bp"
   <<",flow_imbalance_16s_5bp,flow_imbalance_16s_15bp,flow_imbalance_16s_50bp"
   <<",flow_imbalance_32s_5bp,flow_imbalance_32s_15bp,flow_imbalance_32s_50bp"
   <<",insert_pressure_32s,delete_pressure_32s,replenish_pressure_32s,deplete_pressure_32s"
   <<",log1p_non_snapshot_updates_32s,log1p_distinct_local_groups_32s\n";
}

struct RollingSummary {
  std::array<std::array<double,3>,4> signed_flow{};
  std::array<std::array<double,3>,4> abs_flow{};
  uint64_t bid_insert=0,ask_insert=0,bid_delete=0,ask_delete=0;
  uint64_t bid_replenish=0,ask_replenish=0,bid_deplete=0,ask_deplete=0;
  uint64_t updates=0,groups=0;
};

RollingSummary summarize(const std::deque<GroupAgg>& dq,int64_t t){
  const std::array<int64_t,4> win{{1*US,4*US,16*US,32*US}};
  RollingSummary s;
  for(const auto& g:dq){
    if(!g.eligible || g.ts>t) continue;
    const int64_t age=t-g.ts;
    if(age<0 || age>MAX_WINDOW_US) continue;
    for(size_t w=0;w<win.size();++w){
      if(age<=win[w]){
        for(size_t b=0;b<3;++b){
          s.signed_flow[w][b]+=g.signed_flow[b];
          s.abs_flow[w][b]+=g.abs_flow[b];
        }
      }
    }
    s.bid_insert+=g.bid_insert; s.ask_insert+=g.ask_insert;
    s.bid_delete+=g.bid_delete; s.ask_delete+=g.ask_delete;
    s.bid_replenish+=g.bid_replenish; s.ask_replenish+=g.ask_replenish;
    s.bid_deplete+=g.bid_deplete; s.ask_deplete+=g.ask_deplete;
    s.updates+=g.updates; s.groups+=1;
  }
  return s;
}

void emit_support(std::ofstream& out,int64_t t,const Book& book,const std::deque<GroupAgg>& dq){
  out<<t;
  if(!book.valid()){
    out<<",0";
    for(int i=0;i<26;++i) out<<",nan";
    out<<"\n";
    return;
  }
  double b10,a10,b20,a20,b50,a50;
  top_depth(book,b10,a10,b20,a20,b50,a50);
  const auto r=summarize(dq,t);
  out<<std::setprecision(17)<<",1";
  out<<','<<imbalance(b20,a20)<<','<<imbalance(b50,a50);
  out<<','<<std::log1p(b20)<<','<<std::log1p(a20);
  out<<','<<std::log1p(b50)<<','<<std::log1p(a50);
  out<<','<<safe_ratio(b10,b50)<<','<<safe_ratio(a10,a50);
  for(size_t w=0;w<4;++w){
    for(size_t b=0;b<3;++b){
      out<<','<<safe_ratio(r.signed_flow[w][b],r.abs_flow[w][b]);
    }
  }
  out<<','<<safe_ratio(static_cast<double>(r.bid_insert)-static_cast<double>(r.ask_insert),
                      static_cast<double>(r.bid_insert+r.ask_insert));
  out<<','<<safe_ratio(static_cast<double>(r.ask_delete)-static_cast<double>(r.bid_delete),
                      static_cast<double>(r.ask_delete+r.bid_delete));
  out<<','<<safe_ratio(static_cast<double>(r.bid_replenish)-static_cast<double>(r.ask_replenish),
                      static_cast<double>(r.bid_replenish+r.ask_replenish));
  out<<','<<safe_ratio(static_cast<double>(r.ask_deplete)-static_cast<double>(r.bid_deplete),
                      static_cast<double>(r.ask_deplete+r.bid_deplete));
  out<<','<<std::log1p(static_cast<double>(r.updates));
  out<<','<<std::log1p(static_cast<double>(r.groups));
  out<<"\n";
}

} // namespace

int main(int argc,char** argv){
  if(argc!=4){
    std::cerr<<"usage: dev031_p1a_event_depth INPUT.csv.gz SUPPORT.csv OUTPUT.csv\n";
    return 2;
  }
  const std::string input=argv[1], support_path=argv[2], output=argv[3];
  const auto support=read_support(support_path);
  std::ofstream out(output);
  if(!out) throw std::runtime_error("cannot open output");
  write_header(out);

  GzLineReader r(input);
  std::string line;
  if(!r.getline(line)) throw std::runtime_error("missing header");
  const std::string expected="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount";
  if(line!=expected) throw std::runtime_error("unexpected raw header");

  Book book;
  std::deque<GroupAgg> rolling;
  std::vector<Row> group;
  group.reserve(4096);
  int64_t group_ts=std::numeric_limits<int64_t>::min();
  bool group_snapshot=false;
  size_t support_i=0;
  int64_t prev_local=std::numeric_limits<int64_t>::min();
  uint64_t parsed=0,bad=0,groups=0,emitted=0;

  auto trim=[&](int64_t t){
    while(!rolling.empty() && rolling.front().ts < t-MAX_WINDOW_US) rolling.pop_front();
  };

  auto emit_before=[&](int64_t t){
    while(support_i<support.size() && support[support_i]<t){
      trim(support[support_i]);
      emit_support(out,support[support_i],book,rolling);
      ++support_i; ++emitted;
    }
  };

  auto emit_equal=[&](int64_t t){
    while(support_i<support.size() && support[support_i]==t){
      trim(t);
      emit_support(out,t,book,rolling);
      ++support_i; ++emitted;
    }
  };

  auto flush_group=[&](){
    if(group.empty()) return;
    emit_before(group_ts);

    const bool pre_valid=book.valid();
    const double pre_mid=pre_valid ? book.mid() : std::numeric_limits<double>::quiet_NaN();
    GroupAgg agg; agg.ts=group_ts; agg.eligible=pre_valid && !group_snapshot;

    if(group_snapshot){
      book.clear();
    }

    for(const Row& x:group){
      const double q_old=book.qty(x.bid,x.price);
      const double q_new=x.amount;
      if(agg.eligible && !x.snapshot){
        ++agg.updates;
        if(q_old==0.0 && q_new>0.0){ if(x.bid) ++agg.bid_insert; else ++agg.ask_insert; }
        else if(q_old>0.0 && q_new==0.0){ if(x.bid) ++agg.bid_delete; else ++agg.ask_delete; }
        else if(q_old>0.0 && q_new>q_old){ if(x.bid) ++agg.bid_replenish; else ++agg.ask_replenish; }
        else if(q_old>q_new && q_new>0.0){ if(x.bid) ++agg.bid_deplete; else ++agg.ask_deplete; }

        const double dq=q_new-q_old;
        if(dq!=0.0){
          const double dist=10000.0*std::abs(x.price-pre_mid)/pre_mid;
          const double signed_dq=(x.bid ? 1.0 : -1.0)*dq;
          const double abs_dq=std::abs(dq);
          const std::array<double,3> bands{{5.0,15.0,50.0}};
          for(size_t bi=0;bi<bands.size();++bi){
            if(dist<=bands[bi]){
              agg.signed_flow[bi]+=signed_dq;
              agg.abs_flow[bi]+=abs_dq;
            }
          }
        }
      }
      book.apply(x);
    }

    if(group_snapshot){
      book.ready=book.structurally_valid();
    } else if(book.ready && !book.structurally_valid()){
      book.ready=false;
    }

    if(agg.eligible) rolling.push_back(agg);
    trim(group_ts);
    ++groups;
    emit_equal(group_ts);
    group.clear();
    group_snapshot=false;
  };

  while(r.getline(line)){
    ++parsed;
    Row x;
    if(!parse_row(line,x)){ ++bad; continue; }
    if(prev_local!=std::numeric_limits<int64_t>::min() && x.local_ts<prev_local){
      std::cerr<<"local timestamp regression at row "<<parsed<<"\n";
      return 3;
    }
    prev_local=x.local_ts;
    if(group_ts==std::numeric_limits<int64_t>::min()) group_ts=x.local_ts;
    if(x.local_ts!=group_ts){
      flush_group();
      group_ts=x.local_ts;
    }
    group_snapshot=group_snapshot||x.snapshot;
    group.push_back(x);
  }
  flush_group();

  while(support_i<support.size()){
    trim(support[support_i]);
    emit_support(out,support[support_i],book,rolling);
    ++support_i; ++emitted;
  }

  std::cerr<<"parsed_rows="<<parsed<<" bad_rows="<<bad<<" groups="<<groups
           <<" support="<<support.size()<<" emitted="<<emitted<<"\n";
  if(bad!=0 || emitted!=support.size()) return 4;
  return 0;
}
