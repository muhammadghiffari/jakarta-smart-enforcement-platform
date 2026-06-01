import psycopg2
conn = psycopg2.connect('postgresql://jsep_user:jsep_local_dev@localhost:5432/jsep')
cur = conn.cursor()
cur.execute(" SELECT table_name FROM information_schema.tables WHERE table_schema=public ORDER BY table_name\)
tables
