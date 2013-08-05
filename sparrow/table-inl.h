// DON'T INCLUDE DIRECTLY; included from table.h
// Various templatized versions of things that confuse SWIG, etc.

#ifndef TABLE_INL_H_
#define TABLE_INL_H_

#include <boost/utility/enable_if.hpp>

namespace sparrow {

template <class K, class V>
RemoteIterator<K, V>::RemoteIterator(Table *table, int shard, uint32_t fetch_num) :
    table_(table), shard_(shard), done_(false), fetch_num_(fetch_num) {

  request_.set_table(table->id());
  request_.set_shard(shard_);
  request_.set_row_count(fetch_num_);
  int target_worker = table->worker_for_shard(shard);

  // << CRM 2011-01-18 >>
  while (!cached_results.empty())
    cached_results.pop();

  VLOG(3) << "Created RemoteIterator on table " << table->id() << ", shard "
      << shard << " @" << this;
  rpc::NetworkThread::Get()->Call(target_worker + 1, MessageTypes::ITERATOR,
      request_, &response_);
  for (size_t i = 1; i <= response_.row_count(); i++) {
    std::pair < string, string > row;
    row = make_pair(response_.key(i - 1), response_.value(i - 1));
    cached_results.push(row);
  }

  request_.set_id(response_.id());
}

template <class K, class V>
bool RemoteIterator<K, V>::done() {
  return response_.done() && cached_results.empty();
}

template <class K, class V>
void RemoteIterator<K, V>::next() {
  int target_worker = table_->worker_for_shard(shard_);
  if (!cached_results.empty()) cached_results.pop();

  if (cached_results.empty()) {
    if (response_.done()) {
      return;
    }
    rpc::NetworkThread::Get()->Call(target_worker + 1, MessageTypes::ITERATOR,
        request_, &response_);
    if (response_.row_count() < 1 && !response_.done()) LOG(ERROR)
        << "Call to server requesting " << request_.row_count()
        << " rows returned " << response_.row_count() << " rows.";
    for (size_t i = 1; i <= response_.row_count(); i++) {
      std::pair < string, string > row;
      row = make_pair(response_.key(i - 1), response_.value(i - 1));
      cached_results.push(row);
    }
  } else {
    VLOG(4) << "[PREFETCH] Using cached key for Next()";
  }
  ++index_;
}

template <class K, class V>
std::string RemoteIterator<K, V>::key_str() {
  return cached_results.front().first;
}

template <class K, class V>
std::string RemoteIterator<K, V>::value_str() {
  return cached_results.front().second;
}

template<class T>
class Modulo: public SharderT<T> {
  size_t shard_for_key(const T& k, int num_shards) const {
    return boost::hash_value(k) % num_shards;
  }
  DECLARE_REGISTRY_HELPER(Sharder, Modulo);
};
TMPL_DEFINE_REGISTRY_HELPER(Sharder, Modulo);

template<class V>
struct Min: public AccumulatorT<V> {
  void accumulate(V* current, const V& update) const {
    *current = std::min(*current, update);
  }

  DECLARE_REGISTRY_HELPER(Accumulator, Min);
};
TMPL_DEFINE_REGISTRY_HELPER(Accumulator, Min)

template<class V>
struct Max: public AccumulatorT<V> {
  void accumulate(V* current, const V& update) const {
    *current = std::max(*current, update);
  }
  DECLARE_REGISTRY_HELPER(Accumulator, Max);
};
TMPL_DEFINE_REGISTRY_HELPER(Accumulator, Max);

template<class V>
struct Sum: public AccumulatorT<V> {
  void accumulate(V* current, const V& update) const {
    *current += update;
  }
  DECLARE_REGISTRY_HELPER(Accumulator, Sum);
};
TMPL_DEFINE_REGISTRY_HELPER(Accumulator, Sum);

template<class V>
struct Replace: public AccumulatorT<V> {
  void accumulate(V* current, const V& update) const {
    *current = update;
  }
  DECLARE_REGISTRY_HELPER(Accumulator, Replace);
};
TMPL_DEFINE_REGISTRY_HELPER(Accumulator, Replace);

}
 // namespace sparrow

#endif /* TABLE_INL_H_ */
