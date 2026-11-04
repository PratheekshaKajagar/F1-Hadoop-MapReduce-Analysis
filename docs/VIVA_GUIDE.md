# Viva cheat-sheet
* **Why Hadoop?** Distributed storage (HDFS blocks + replication) and parallel processing (MapReduce) of lap-level records; scales out horizontally. Be honest: data here is ~4 MB.
* **What is a mapper/reducer here?** Mapper parses CSV lines and emits `key<TAB>value`; Hadoop sorts/shuffles by key; reducer receives all values of a key and computes the metric.
* **Map-side join:** small tables (races, constructors) shipped with `-files` (distributed cache) and loaded in memory in each mapper.
* **In-mapper combining:** Jobs 1/3/6 aggregate laps per driver-race inside the mapper -> 189,106 lap records become 3,369 shuffled records (see `logs/job1_driver_performance.log`).
* **Job chaining:** Job 0 output (race baseline) is input side-data for Jobs 1,3,5,6.
* **Why normalise lap times?** Circuits differ in length; relative-to-race-median pace is comparable.
* **What if asked "is it really HDFS?"** In the build sandbox it was the Hadoop FileSystem API on local disk; run `MODE=cluster` on your pseudo-distributed install to show real HDFS (fsck, UI).
* **Validation:** `results/validation_report.txt` - pandas recomputation matches Hadoop; Hadoop points reproduce official standings except two FIA penalties.
* **K-Means:** unsupervised grouping, not prediction; elbow + silhouette.
