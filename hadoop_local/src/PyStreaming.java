import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.*;
import org.apache.hadoop.conf.*;
import org.apache.hadoop.fs.Path;
import org.apache.hadoop.io.*;
import org.apache.hadoop.mapreduce.*;
import org.apache.hadoop.mapreduce.lib.input.*;
import org.apache.hadoop.mapreduce.lib.output.*;
import org.apache.hadoop.util.*;

/**
 * PyStreaming - a minimal re-implementation of Hadoop Streaming's contract
 * (org.apache.hadoop.streaming.StreamJob) on top of the genuine Hadoop MapReduce API.
 *
 * Hadoop's own InputFormat / split / sort-shuffle / partitioner / reduce-task scheduling /
 * OutputCommitter do ALL of the framework work. This class only pipes records to an external
 * program over stdin/stdout ("key<TAB>value" lines), exactly like hadoop-streaming.jar does.
 * The Python mapper/reducer scripts are therefore fully compatible with the official streaming jar
 * (see scripts/run_on_cluster.sh).
 *
 * Usage: PyStreaming [-D k=v] [-files f1,f2] -input P [-input P2 ...] -output O
 *        -mapper "python3 m.py" [-reducer "python3 r.py"] [-numReduceTasks N] [-name NAME]
 */
public class PyStreaming extends Configured implements Tool {

  static final String MAPPER_CMD = "pystreaming.mapper.cmd";
  static final String REDUCER_CMD = "pystreaming.reducer.cmd";

  /** Runs an external command; feeds stdin; collects "key\tvalue" lines from stdout. */
  static class PipeProcess {
    final Process proc;
    final Writer stdin;
    final BlockingQueue<String> out = new LinkedBlockingQueue<String>();
    final Thread outThread, errThread;

    PipeProcess(String cmd, Map<String, String> env) throws IOException {
      ProcessBuilder pb = new ProcessBuilder("/bin/sh", "-c", cmd);
      pb.environment().putAll(env);
      proc = pb.start();
      stdin = new BufferedWriter(new OutputStreamWriter(proc.getOutputStream(), StandardCharsets.UTF_8), 1 << 16);
      outThread = new Thread(new Runnable() {
        public void run() {
          try (BufferedReader r = new BufferedReader(new InputStreamReader(proc.getInputStream(), StandardCharsets.UTF_8))) {
            String l;
            while ((l = r.readLine()) != null) out.add(l);
          } catch (IOException e) { /* surfaces via exit code */ }
        }
      });
      errThread = new Thread(new Runnable() {
        public void run() {
          try (BufferedReader r = new BufferedReader(new InputStreamReader(proc.getErrorStream(), StandardCharsets.UTF_8))) {
            String l;
            while ((l = r.readLine()) != null) System.err.println("[python-stderr] " + l);
          } catch (IOException e) { }
        }
      });
      outThread.setDaemon(true);
      errThread.setDaemon(true);
      outThread.start();
      errThread.start();
    }

    void finish() throws IOException, InterruptedException {
      stdin.close();
      int rc = proc.waitFor();
      outThread.join();
      errThread.join();
      if (rc != 0) throw new IOException("subprocess exited with code " + rc);
    }
  }

  static void emit(String line, TaskInputOutputContext<?, ?, Text, Text> ctx, boolean nullValueOk)
      throws IOException, InterruptedException {
    int t = line.indexOf('\t');
    if (t < 0) ctx.write(new Text(line), nullValueOk ? null : new Text(""));
    else ctx.write(new Text(line.substring(0, t)), new Text(line.substring(t + 1)));
  }

  /** Same convention as Hadoop Streaming: job conf keys exported as env vars with '.' -> '_'. */
  static Map<String, String> taskEnv(Configuration conf, InputSplit split) {
    Map<String, String> env = new HashMap<String, String>();
    for (Map.Entry<String, String> e : conf) {
      if (e.getKey().startsWith("pystreaming.")) continue;
      if (e.getValue() == null) continue;
      env.put(e.getKey().replace('.', '_').replace('-', '_'), e.getValue());
    }
    if (split instanceof FileSplit) {
      String p = ((FileSplit) split).getPath().toString();
      env.put("mapreduce_map_input_file", p);
      env.put("map_input_file", p);
    }
    return env;
  }

  public static class PyMapper extends Mapper<LongWritable, Text, Text, Text> {
    PipeProcess pp;
    boolean mapOnly;

    @Override protected void setup(Context ctx) throws IOException {
      mapOnly = ctx.getNumReduceTasks() == 0;
      pp = new PipeProcess(ctx.getConfiguration().get(MAPPER_CMD), taskEnv(ctx.getConfiguration(), ctx.getInputSplit()));
    }
    void drain(Context ctx) throws IOException, InterruptedException {
      String l;
      while ((l = pp.out.poll()) != null) emit(l, ctx, mapOnly);
    }
    @Override protected void map(LongWritable k, Text v, Context ctx) throws IOException, InterruptedException {
      pp.stdin.write(v.toString());
      pp.stdin.write('\n');
      drain(ctx);
    }
    @Override protected void cleanup(Context ctx) throws IOException, InterruptedException {
      pp.finish();
      drain(ctx);
    }
  }

  public static class PyReducer extends Reducer<Text, Text, Text, Text> {
    PipeProcess pp;

    @Override protected void setup(Context ctx) throws IOException {
      pp = new PipeProcess(ctx.getConfiguration().get(REDUCER_CMD), taskEnv(ctx.getConfiguration(), null));
    }
    void drain(Context ctx) throws IOException, InterruptedException {
      String l;
      while ((l = pp.out.poll()) != null) emit(l, ctx, true);
    }
    @Override protected void reduce(Text k, Iterable<Text> vals, Context ctx) throws IOException, InterruptedException {
      String key = k.toString();
      for (Text v : vals) {
        pp.stdin.write(key);
        pp.stdin.write('\t');
        pp.stdin.write(v.toString());
        pp.stdin.write('\n');
      }
      drain(ctx);
    }
    @Override protected void cleanup(Context ctx) throws IOException, InterruptedException {
      pp.finish();
      drain(ctx);
    }
  }

  @Override public int run(String[] args) throws Exception {
    Configuration conf = getConf();
    List<String> inputs = new ArrayList<String>();
    String output = null, mapper = null, reducer = null, name = "pystreaming";
    int reduces = 1;
    for (int i = 0; i < args.length; i++) {
      String a = args[i];
      if (a.equals("-input")) inputs.add(args[++i]);
      else if (a.equals("-output")) output = args[++i];
      else if (a.equals("-mapper")) mapper = args[++i];
      else if (a.equals("-reducer")) reducer = args[++i];
      else if (a.equals("-numReduceTasks")) reduces = Integer.parseInt(args[++i]);
      else if (a.equals("-name")) name = args[++i];
      else { System.err.println("unknown arg " + a); return 2; }
    }
    if (inputs.isEmpty() || output == null || mapper == null) {
      System.err.println("missing -input / -output / -mapper");
      return 2;
    }
    if (reducer == null) reduces = 0;
    conf.set(MAPPER_CMD, mapper);
    if (reducer != null) conf.set(REDUCER_CMD, reducer);
    Job job = Job.getInstance(conf, name);
    job.setJarByClass(PyStreaming.class);
    job.setMapperClass(PyMapper.class);
    if (reducer != null) job.setReducerClass(PyReducer.class);
    job.setNumReduceTasks(reduces);
    job.setInputFormatClass(TextInputFormat.class);
    job.setOutputFormatClass(TextOutputFormat.class);
    job.setMapOutputKeyClass(Text.class);
    job.setMapOutputValueClass(Text.class);
    job.setOutputKeyClass(Text.class);
    job.setOutputValueClass(Text.class);
    for (String in : inputs) FileInputFormat.addInputPath(job, new Path(in));
    FileOutputFormat.setOutputPath(job, new Path(output));
    return job.waitForCompletion(true) ? 0 : 1;
  }

  public static void main(String[] args) throws Exception {
    System.exit(ToolRunner.run(new Configuration(), new PyStreaming(), args));
  }
}
