#!/usr/bin/env bash
# Common environment.  MODE=local  -> bundled Apache Hadoop 3.3.4 libraries (MapReduce engine + FileSystem shell), runs anywhere with Java 8+
#                      MODE=cluster -> your real Hadoop install (HADOOP_HOME set, HDFS + YARN running); uses the official hadoop-streaming jar
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${MODE:-local}"
MR="$PROJECT/src/mapreduce"
LOGS="$PROJECT/logs"; mkdir -p "$LOGS"
F1_OUT="/f1/output"

if [ "$MODE" = "cluster" ]; then
  : "${HADOOP_HOME:?set HADOOP_HOME for MODE=cluster}"
  HDFS_ROOT=""                                   # default filesystem = hdfs://namenode:port from core-site.xml
  STREAMING_JAR="$(ls "$HADOOP_HOME"/share/hadoop/tools/lib/hadoop-streaming-*.jar | head -1)"
  hdfs_dfs()      { "$HADOOP_HOME/bin/hdfs" dfs "$@"; }
  run_streaming() { "$HADOOP_HOME/bin/hadoop" jar "$STREAMING_JAR" "$@"; }
else
  HLIB="$PROJECT/hadoop_local/lib"
  HDFS_ROOT="file://$PROJECT/hdfs_local"         # Hadoop FileSystem API rooted in ./hdfs_local (see docs: local mode = file:// not hdfs://)
  JOPTS="-Dlog4j2.configurationFile=$PROJECT/hadoop_local/conf/log4j2.properties"
  hdfs_dfs()      { java $JOPTS -cp "$HLIB/*:$PROJECT/hadoop_local/conf" org.apache.hadoop.fs.FsShell -D fs.defaultFS=file:/// "$@"; }
  run_streaming() { ( mkdir -p "$PROJECT/hdfs_local/work" && cd "$PROJECT/hdfs_local/work" && java $JOPTS -Xmx1500m -cp "$HLIB/*:$PROJECT/hadoop_local/conf" PyStreaming -D mapreduce.framework.name=local -D fs.defaultFS=file:/// \
                    -D hadoop.tmp.dir="$PROJECT/hdfs_local/tmp" -D mapreduce.job.reduce.slowstart.completedmaps=1.0 "$@" ); }
fi
H() { echo "${HDFS_ROOT}/f1/$1"; }                # HDFS path helper
