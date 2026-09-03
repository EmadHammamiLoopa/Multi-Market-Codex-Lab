#include <zlib.h>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

class GzReader {
 public:
  explicit GzReader(const std::string& path) {
    f_=gzopen(path.c_str(),"rb");
    if(!f_) throw std::runtime_error("open:"+path);
    buf_.resize(1<<20);
  }
  ~GzReader(){ if(f_) gzclose(f_); }
  bool get(std::string& out){
    out.clear();
    for(;;){
      char* p=gzgets(f_,buf_.data(),static_cast<int>(buf_.size()));
      if(!p) return !out.empty();
      size_t n=std::strlen(p);
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

template<size_t N>
bool split(const std::string& s,std::array<std::string,N>& f){
  size_t start=0,k=0;
  for(size_t i=0;i<=s.size();++i){
    if(i==s.size()||s[i]==','){
      if(k>=N) return false;
      f[k++]=s.substr(start,i-start);
      start=i+1;
    }
  }
  return k==N;
}

struct Stats {
  uint64_t rows=0,bad=0,snapshot_rows=0,non_snapshot_rows=0;
  uint64_t bid_rows=0,ask_rows=0,buy_rows=0,sell_rows=0,unknown_rows=0;
  uint64_t zero_qty_rows=0,negative_feed_latency=0;
  uint64_t local_regressions=0,exchange_regressions=0;
  int64_t min_exch=std::numeric_limits<int64_t>::max();
  int64_t max_exch=std::numeric_limits<int64_t>::min();
  int64_t min_local=std::numeric_limits<int64_t>::max();
  int64_t max_local=std::numeric_limits<int64_t>::min();
  int64_t min_feed=std::numeric_limits<int64_t>::max();
  int64_t max_feed=std::numeric_limits<int64_t>::min();
  long double sum_feed=0.0L;
};

bool parse_bool(const std::string& x,bool& out){
  if(x=="true"){out=true;return true;}
  if(x=="false"){out=false;return true;}
  return false;
}

void observe_ts(Stats& s,int64_t exch,int64_t local,int64_t& prev_local,int64_t& prev_exch){
  if(prev_local!=std::numeric_limits<int64_t>::min() && local<prev_local) ++s.local_regressions;
  if(prev_exch!=std::numeric_limits<int64_t>::min() && exch<prev_exch) ++s.exchange_regressions;
  prev_local=local; prev_exch=exch;
  s.min_exch=std::min(s.min_exch,exch); s.max_exch=std::max(s.max_exch,exch);
  s.min_local=std::min(s.min_local,local); s.max_local=std::max(s.max_local,local);
  const int64_t feed=local-exch;
  if(feed<0) ++s.negative_feed_latency;
  s.min_feed=std::min(s.min_feed,feed); s.max_feed=std::max(s.max_feed,feed);
  s.sum_feed+=static_cast<long double>(feed);
}

Stats scan_l2(const std::string& path){
  GzReader r(path); std::string z;
  if(!r.get(z)) throw std::runtime_error("l2_missing_header");
  if(z!="exchange,symbol,timestamp,local_timestamp,is_snapshot,side,price,amount")
    throw std::runtime_error("l2_header:"+z);
  Stats s; int64_t pl=std::numeric_limits<int64_t>::min(),pe=pl;
  while(r.get(z)){
    ++s.rows; std::array<std::string,8> f{};
    if(!split(z,f)){++s.bad;continue;}
    try{
      const int64_t exch=std::stoll(f[2]),local=std::stoll(f[3]);
      bool snap=false; if(!parse_bool(f[4],snap)){++s.bad;continue;}
      if(f[5]!="bid" && f[5]!="ask"){++s.bad;continue;}
      const double px=std::stod(f[6]),qty=std::stod(f[7]);
      if(!std::isfinite(px)||px<=0||!std::isfinite(qty)||qty<0){++s.bad;continue;}
      observe_ts(s,exch,local,pl,pe);
      if(snap) ++s.snapshot_rows; else ++s.non_snapshot_rows;
      if(f[5]=="bid") ++s.bid_rows; else ++s.ask_rows;
      if(qty==0) ++s.zero_qty_rows;
    }catch(...){++s.bad;}
  }
  return s;
}

Stats scan_trades(const std::string& path){
  GzReader r(path); std::string z;
  if(!r.get(z)) throw std::runtime_error("trade_missing_header");
  if(z!="exchange,symbol,timestamp,local_timestamp,id,side,price,amount")
    throw std::runtime_error("trade_header:"+z);
  Stats s; int64_t pl=std::numeric_limits<int64_t>::min(),pe=pl;
  while(r.get(z)){
    ++s.rows; std::array<std::string,8> f{};
    if(!split(z,f)){++s.bad;continue;}
    try{
      const int64_t exch=std::stoll(f[2]),local=std::stoll(f[3]);
      if(f[4].empty()){++s.bad;continue;}
      if(f[5]!="buy" && f[5]!="sell" && f[5]!="unknown"){++s.bad;continue;}
      const double px=std::stod(f[6]),qty=std::stod(f[7]);
      if(!std::isfinite(px)||px<=0||!std::isfinite(qty)||qty<0){++s.bad;continue;}
      observe_ts(s,exch,local,pl,pe);
      if(f[5]=="buy") ++s.buy_rows;
      else if(f[5]=="sell") ++s.sell_rows;
      else ++s.unknown_rows;
      if(qty==0) ++s.zero_qty_rows;
    }catch(...){++s.bad;}
  }
  return s;
}

void emit(const char* kind,const Stats& s){
  const long double mean=s.rows? s.sum_feed/static_cast<long double>(s.rows):0.0L;
  std::cout<<"{"
    <<"\"kind\":\""<<kind<<"\""
    <<",\"rows\":"<<s.rows
    <<",\"bad_rows\":"<<s.bad
    <<",\"snapshot_rows\":"<<s.snapshot_rows
    <<",\"non_snapshot_rows\":"<<s.non_snapshot_rows
    <<",\"bid_rows\":"<<s.bid_rows
    <<",\"ask_rows\":"<<s.ask_rows
    <<",\"buy_rows\":"<<s.buy_rows
    <<",\"sell_rows\":"<<s.sell_rows
    <<",\"unknown_rows\":"<<s.unknown_rows
    <<",\"zero_qty_rows\":"<<s.zero_qty_rows
    <<",\"local_regressions\":"<<s.local_regressions
    <<",\"exchange_regressions\":"<<s.exchange_regressions
    <<",\"negative_feed_latency\":"<<s.negative_feed_latency
    <<",\"min_exchange_ts\":"<<(s.rows?s.min_exch:0)
    <<",\"max_exchange_ts\":"<<(s.rows?s.max_exch:0)
    <<",\"min_local_ts\":"<<(s.rows?s.min_local:0)
    <<",\"max_local_ts\":"<<(s.rows?s.max_local:0)
    <<",\"min_feed_latency_us\":"<<(s.rows?s.min_feed:0)
    <<",\"max_feed_latency_us\":"<<(s.rows?s.max_feed:0)
    <<",\"mean_feed_latency_us\":"<<static_cast<double>(mean)
    <<"}\n";
}

} // namespace

int main(int argc,char** argv){
  if(argc!=3){
    std::cerr<<"usage: dev045_m0_raw_scan L2.csv.gz TRADES.csv.gz\n";
    return 2;
  }
  try{
    const auto l2=scan_l2(argv[1]);
    const auto tr=scan_trades(argv[2]);
    emit("incremental_book_L2",l2);
    emit("trades",tr);
    if(
      l2.rows==0 || tr.rows==0 || l2.bad!=0 || tr.bad!=0 ||
      l2.snapshot_rows==0 || l2.bid_rows==0 || l2.ask_rows==0 ||
      tr.buy_rows==0 || tr.sell_rows==0 ||
      l2.local_regressions!=0 || tr.local_regressions!=0 ||
      l2.negative_feed_latency!=0 || tr.negative_feed_latency!=0
    ) return 4;
    return 0;
  }catch(const std::exception& e){
    std::cerr<<e.what()<<"\n";
    return 3;
  }
}
