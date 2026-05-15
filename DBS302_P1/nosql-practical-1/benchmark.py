import time
import uuid
import redis
import pymongo
from cassandra.cluster import Cluster

r = redis.Redis(host='172.24.0.2', port=6379, decode_responses=True)

mongo_client = pymongo.MongoClient('mongodb://admin:password123@172.24.0.3:27017/')
mongo_db = mongo_client['benchmark_db']
mongo_posts = mongo_db['posts']
mongo_posts.drop()

cass_cluster = Cluster(['127.0.0.1'])
cass_session = cass_cluster.connect()
cass_session.execute("CREATE KEYSPACE IF NOT EXISTS benchmark WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1}")
cass_session.set_keyspace('benchmark')
cass_session.execute('DROP TABLE IF EXISTS posts_bench')
cass_session.execute('''CREATE TABLE posts_bench (
    user_id UUID, post_id UUID, content TEXT, created_at TIMESTAMP,
    PRIMARY KEY (user_id, created_at, post_id)
) WITH CLUSTERING ORDER BY (created_at DESC, post_id ASC)''')

NUM_WRITES = 500
user_id = 'user_bench_001'
cass_user_id = uuid.UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')

print(f'--- Write Benchmark ({NUM_WRITES} records) ---')

start = time.time()
pipe = r.pipeline()
for i in range(NUM_WRITES):
    pid = f'bench_post_{i}'
    pipe.hset(f'post:{pid}', mapping={'user_id': user_id, 'content': f'Post {i}', 'timestamp': '2025-05-01'})
    pipe.lpush(f'timeline:{user_id}', pid)
pipe.execute()
t = time.time() - start
print(f'  Redis   : {t:.4f}s  ({NUM_WRITES/t:.0f} ops/sec)')

start = time.time()
mongo_posts.insert_many([{'_id': f'bench_post_{i}', 'user_id': user_id, 'content': f'Post {i}'} for i in range(NUM_WRITES)])
t = time.time() - start
print(f'  MongoDB : {t:.4f}s  ({NUM_WRITES/t:.0f} ops/sec)')

prepared = cass_session.prepare('INSERT INTO posts_bench (user_id, post_id, content, created_at) VALUES (?, ?, ?, toTimestamp(now()))')
start = time.time()
for i in range(NUM_WRITES):
    cass_session.execute(prepared, (cass_user_id, uuid.uuid4(), f'Post {i}'))
t = time.time() - start
print(f'  Cassandra: {t:.4f}s  ({NUM_WRITES/t:.0f} ops/sec)')

print(f'--- Read Benchmark ({NUM_WRITES} records) ---')

start = time.time()
pids = r.lrange(f'timeline:{user_id}', 0, NUM_WRITES-1)
pipe = r.pipeline()
for pid in pids:
    pipe.hgetall(f'post:{pid}')
pipe.execute()
t = time.time() - start
print(f'  Redis   : {t:.4f}s  ({NUM_WRITES/t:.0f} ops/sec)')

mongo_posts.create_index([('user_id', pymongo.ASCENDING)])
start = time.time()
results = list(mongo_posts.find({'user_id': user_id}))
t = time.time() - start
print(f'  MongoDB : {t:.4f}s  ({len(results)/t:.0f} ops/sec)')

start = time.time()
rows = list(cass_session.execute('SELECT * FROM posts_bench WHERE user_id = %s LIMIT %s', (cass_user_id, NUM_WRITES)))
t = time.time() - start
print(f'  Cassandra: {t:.4f}s  ({len(rows)/t:.0f} ops/sec)')

print('--- Benchmark Complete ---')
mongo_client.close()
cass_cluster.shutdown()
