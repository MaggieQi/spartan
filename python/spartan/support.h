#ifndef PYTHON_SUPPORT_H
#define PYTHON_SUPPORT_H

#include <Python.h>
#include <string>

namespace spartan {

class Master;
class Worker;
class Table;
class TableIterator;
class Kernel;
class TableContext;

enum LogLevel {
    FATAL = 0, ERROR = 1, WARN = 2, INFO = 3, DEBUG = 4
};

void set_log_level(LogLevel level);
void log(const char* file, int line, const char* msg);

Master* start_master(int port, int num_workers);
Worker* start_worker(const std::string& master, int port);

void shutdown(Master*);
void wait_for_workers(Master*);
Table* create_table(Master*, PyObject* sharder, PyObject* accum, PyObject* selector);
void destroy_table(Master*, Table*);

TableContext* get_context();

void foreach_shard(Master* m, Table* t, PyObject* fn, PyObject* args);
Table* get_table(Kernel* k, int id);
int current_table(Kernel* k);
int current_shard(Kernel* k);

// Table operations
Table* get_table(TableContext*, int table_id);
PyObject* get_sharder(Table*);
PyObject* get_accum(Table*);
PyObject* get_selector(Table*);
PyObject* get(Table*, PyObject* k);
void update(Table*, PyObject* k, PyObject* v);
int get_id(Table* t);
int num_shards(Table* t);


// Iterators
TableIterator* get_iterator(Table*, int shard);
PyObject* iter_key(TableIterator*);
PyObject* iter_value(TableIterator*);
bool iter_done(TableIterator*);
void iter_next(TableIterator*);

// Hack to allow passing Kernel* to user functions.
static inline Kernel* cast_to_kernel(long kernel_handle) {
  return (Kernel*)kernel_handle;
}

Master* cast_to_master(TableContext* ctx);

}

#endif // PYTHON_SUPPORT_H
