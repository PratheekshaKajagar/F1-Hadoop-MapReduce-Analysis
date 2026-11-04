# Running on a real Hadoop cluster (pseudo-distributed, ~15 min)
1. Install Java 8/11 and download Hadoop 3.3.x from https://hadoop.apache.org/releases.html ; `export HADOOP_HOME=/opt/hadoop`.
2. `core-site.xml`: `fs.defaultFS = hdfs://localhost:9000`; `hdfs-site.xml`: `dfs.replication = 1`; `mapred-site.xml`: `mapreduce.framework.name = yarn`; configure `yarn-site.xml` (`mapreduce_shuffle`).
3. `hdfs namenode -format && start-dfs.sh && start-yarn.sh` ; check `jps` (NameNode, DataNode, ResourceManager, NodeManager) and http://localhost:9870 / :8088.
4. Python 3 must be installed on every node. From the project: `MODE=cluster ./scripts/run_all.sh`
5. Evidence for the viva: `hdfs dfs -ls -R /f1`, `hdfs fsck /f1 -files -blocks`, YARN UI job history, `hdfs dfs -cat /f1/output/job1_driver_performance/part-r-00000`.
Equivalent raw command (what `03_run_mapreduce.sh` does):
`hadoop jar $HADOOP_HOME/share/hadoop/tools/lib/hadoop-streaming-*.jar -files common.py,job1_mapper.py,job1_reducer.py,/f1/output/job0_race_baseline/part-r-00000#race_baseline.tsv,/f1/pitstops/pitstops.csv -input /f1/laps -output /f1/output/job1 -mapper "env PYTHONPATH=. python3 job1_mapper.py" -reducer "env PYTHONPATH=. python3 job1_reducer.py" -numReduceTasks 2`
Unit-test any job without Hadoop: `cat file | python3 mapper.py | sort | python3 reducer.py` (set `mapreduce_map_input_file` for multi-input jobs).
