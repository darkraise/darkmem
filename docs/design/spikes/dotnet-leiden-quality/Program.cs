using System.Diagnostics;
using System.Text.Json;

// darkmem Leiden quality/scale spike (#15): FULL Leiden (local move + randomized
// well-connectedness refinement + constrained aggregation, RBConfiguration quality)
// in pure managed C#, validated against leidenalg's production output on the same
// graphs — including the real darkmem code graph exported from the dev DB.
//
// Usage: dotnet run -c Release -- <graphs-dir>   (run export_graphs.py + python_reference.py first)

var dir = args.Length > 0 ? args[0] : "graphs";
const int LargeGraphThreshold = 10_000;   // community_detector.py regime switch
bool allPass = true;

Console.WriteLine("=== darkmem Leiden quality spike (pure-managed full Leiden vs leidenalg) ===\n");

foreach (var path in Directory.GetFiles(dir, "*.txt").OrderBy(p => p))
{
    var name = Path.GetFileNameWithoutExtension(path);
    var graph = Graph.Load(path);
    var (gamma, iters) = graph.N > LargeGraphThreshold ? (2.0, 3) : (1.0, -1);

    var sw = Stopwatch.StartNew();
    var membership = Leiden.Run(graph, gamma, iters, seed: 0);
    sw.Stop();

    double qManaged = graph.RbModularity(membership, gamma);
    int comms = membership.Distinct().Count();
    Console.WriteLine($"[{name}] n={graph.N} m={graph.M} gamma={gamma}");
    Console.WriteLine($"  managed : comms={comms} Q_rb={qManaged:F4} {sw.Elapsed.TotalSeconds:F2}s");

    var pyPath = Path.Combine(dir, name + ".python.json");
    if (File.Exists(pyPath))
    {
        var py = JsonSerializer.Deserialize<PyRef>(File.ReadAllText(pyPath),
            new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower })!;
        double qPyRecomputed = graph.RbModularity(py.Membership, gamma);
        if (Math.Abs(qPyRecomputed - py.RbModularity) > 1e-6)
        {
            Console.WriteLine($"  METRIC MISMATCH: C# Q of python membership {qPyRecomputed:F6} != python-reported {py.RbModularity:F6}");
            allPass = false;
        }
        double nmi = Metrics.Nmi(membership, py.Membership);
        double tolerance = Math.Max(0.005, 0.01 * Math.Abs(py.RbModularity));
        bool qOk = qManaged >= py.RbModularity - tolerance;
        Console.WriteLine($"  python  : comms={py.Communities} Q_rb={py.RbModularity:F4} {py.Seconds:F2}s");
        Console.WriteLine($"  compare : dQ={qManaged - py.RbModularity:+0.0000;-0.0000} NMI(managed,python)={nmi:F3} quality-parity={(qOk ? "PASS" : "FAIL")}");
        if (!qOk) allPass = false;
    }

    var plantedPath = Path.Combine(dir, name + ".planted");
    if (File.Exists(plantedPath))
    {
        var planted = File.ReadAllLines(plantedPath).Where(l => l.Length > 0).Select(int.Parse).ToArray();
        double nmiPlanted = Metrics.Nmi(membership, planted);
        bool plantedOk = nmiPlanted >= 0.95;
        Console.WriteLine($"  planted : NMI(managed,planted)={nmiPlanted:F3} {(plantedOk ? "PASS" : "FAIL")}");
        if (!plantedOk) allPass = false;
    }

    if (graph.N > LargeGraphThreshold)
    {
        bool timeOk = sw.Elapsed.TotalSeconds < 60;   // community_detector.py prod timeout
        Console.WriteLine($"  scale   : {sw.Elapsed.TotalSeconds:F2}s vs 60s prod timeout {(timeOk ? "PASS" : "FAIL")}");
        if (!timeOk) allPass = false;
    }
    Console.WriteLine();
}

Console.WriteLine($"[verdict] pure-managed full Leiden quality/scale vs leidenalg: {(allPass ? "PASS" : "FAIL")}");
Environment.Exit(allPass ? 0 : 1);

record PyRef(int N, int M, double Gamma, int Communities, double RbModularity, double Seconds, int[] Membership);

// Undirected weighted graph; parallel edges merged into weights, self-loops kept.
sealed class Graph
{
    public int N;
    public long M;                                  // edge count as loaded (for Q_rb's per-edge normalization)
    public (int To, double W)[][] Adj = [];         // self-loops excluded here
    public double[] SelfW = [];                     // self-loop weight per node (counted once)
    public double[] K = [];                         // weighted degree (self-loop counts 2)
    public double TwoM;                             // sum of K

    public static Graph Load(string path)
    {
        var lines = File.ReadAllLines(path);
        int n = int.Parse(lines[0]);
        var w = new Dictionary<long, double>();
        var selfW = new double[n];
        long m = 0;
        for (int i = 1; i < lines.Length; i++)
        {
            if (lines[i].Length == 0) continue;
            var sp = lines[i].Split(' ');
            int s = int.Parse(sp[0]), t = int.Parse(sp[1]);
            m++;
            if (s == t) { selfW[s] += 1; continue; }
            long key = Math.Min(s, t) * (long)n + Math.Max(s, t);
            w[key] = w.GetValueOrDefault(key) + 1;
        }
        var counts = new int[n];
        foreach (var key in w.Keys) { counts[(int)(key / n)]++; counts[(int)(key % n)]++; }
        var adj = new (int, double)[n][];
        for (int v = 0; v < n; v++) adj[v] = new (int, double)[counts[v]];
        var fill = new int[n];
        foreach (var (key, weight) in w)
        {
            int a = (int)(key / n), b = (int)(key % n);
            adj[a][fill[a]++] = (b, weight);
            adj[b][fill[b]++] = (a, weight);
        }
        var g = new Graph { N = n, M = m, Adj = adj, SelfW = selfW, K = new double[n] };
        for (int v = 0; v < n; v++)
        {
            double k = 2 * selfW[v];
            foreach (var (_, weight) in adj[v]) k += weight;
            g.K[v] = k;
            g.TwoM += k;
        }
        return g;
    }

    // Q = sum_c [ w_in(c)/m_w - gamma * (d_c/(2m_w))^2 ] with weights; matches python_reference.py.
    public double RbModularity(int[] membership, double gamma)
    {
        double mw = TwoM / 2;
        if (mw == 0) return 0;
        var win = new Dictionary<int, double>();
        var dsum = new Dictionary<int, double>();
        for (int v = 0; v < N; v++)
        {
            if (SelfW[v] > 0) win[membership[v]] = win.GetValueOrDefault(membership[v]) + SelfW[v];
            foreach (var (to, weight) in Adj[v])
                if (to > v && membership[v] == membership[to])
                    win[membership[v]] = win.GetValueOrDefault(membership[v]) + weight;
            dsum[membership[v]] = dsum.GetValueOrDefault(membership[v]) + K[v];
        }
        double q = 0;
        foreach (var (c, d) in dsum)
            q += win.GetValueOrDefault(c) / mw - gamma * (d / TwoM) * (d / TwoM);
        return q;
    }
}

static class Leiden
{
    // Full Leiden: fast local move -> well-connectedness refinement -> aggregation
    // constrained by the unrefined partition; repeats until stable (or maxIterations).
    public static int[] Run(Graph g, double gamma, int maxIterations, int seed)
    {
        var rng = new Random(seed);
        var level = g;
        var toOrig = Enumerable.Range(0, g.N).ToArray();   // original node -> current level node
        int[] finalMembership = Enumerable.Range(0, g.N).ToArray();
        int iteration = 0;

        while (true)
        {
            var membership = Enumerable.Range(0, level.N).ToArray();
            bool improved = LocalMove(level, membership, gamma, rng);
            Renumber(membership);

            for (int v = 0; v < g.N; v++) finalMembership[v] = membership[toOrig[v]];
            iteration++;
            bool lastRound = !improved || (maxIterations > 0 && iteration >= maxIterations);

            var refined = Refine(level, membership, gamma, rng);
            int refinedCount = Renumber(refined);
            if (refinedCount == level.N && lastRound) break;   // fully converged: every refined community is a singleton
            if (lastRound) break;

            // Aggregate over the refined partition; seed next level's communities from `membership`.
            level = Aggregate(level, refined, refinedCount, out var refinedOfLevelNode);
            var next = new int[g.N];
            for (int v = 0; v < g.N; v++) next[v] = refinedOfLevelNode[toOrig[v]];
            toOrig = next;
        }
        Renumber(finalMembership);
        return finalMembership;
    }

    static bool LocalMove(Graph g, int[] membership, double gamma, Random rng)
    {
        var commDeg = new double[g.N];
        for (int v = 0; v < g.N; v++) commDeg[membership[v]] += g.K[v];

        var queue = new Queue<int>();
        var inQueue = new bool[g.N];
        var order = Enumerable.Range(0, g.N).ToArray();
        Shuffle(order, rng);
        foreach (var v in order) { queue.Enqueue(v); inQueue[v] = true; }

        var wTo = new Dictionary<int, double>();
        bool improvedEver = false;
        while (queue.Count > 0)
        {
            int v = queue.Dequeue();
            inQueue[v] = false;
            int cv = membership[v];
            wTo.Clear();
            wTo[cv] = 0;
            foreach (var (to, w) in g.Adj[v]) wTo[membership[to]] = wTo.GetValueOrDefault(membership[to]) + w;

            double baseGain = wTo[cv] - gamma * g.K[v] * (commDeg[cv] - g.K[v]) / g.TwoM;
            int best = cv;
            double bestGain = 0;
            foreach (var (c, w) in wTo)
            {
                if (c == cv) continue;
                double gain = (w - gamma * g.K[v] * commDeg[c] / g.TwoM) - baseGain;
                if (gain > bestGain + 1e-12) { bestGain = gain; best = c; }
            }
            if (best != cv)
            {
                commDeg[cv] -= g.K[v];
                commDeg[best] += g.K[v];
                membership[v] = best;
                improvedEver = true;
                foreach (var (to, _) in g.Adj[v])
                    if (membership[to] != best && !inQueue[to]) { queue.Enqueue(to); inQueue[to] = true; }
            }
        }
        return improvedEver;
    }

    // Leiden refinement: within each community C, grow sub-communities from singletons.
    // Only well-connected nodes merge, only into well-connected sub-communities, and the
    // target is chosen uniformly at random among positive-gain candidates (seeded RNG).
    static int[] Refine(Graph g, int[] membership, double gamma, Random rng)
    {
        var refined = Enumerable.Range(0, g.N).ToArray();
        var nodesOf = new Dictionary<int, List<int>>();
        for (int v = 0; v < g.N; v++)
        {
            if (!nodesOf.TryGetValue(membership[v], out var list)) nodesOf[membership[v]] = list = [];
            list.Add(v);
        }

        var subDeg = new double[g.N];         // per refined community: total degree
        var subExt = new double[g.N];         // per refined community: weight to rest of C
        var subSize = new int[g.N];
        var wToSub = new Dictionary<int, double>();
        var candidates = new List<int>();

        foreach (var (_, nodes) in nodesOf)
        {
            if (nodes.Count == 1) continue;
            double commDegTotal = 0;
            foreach (var v in nodes) commDegTotal += g.K[v];
            foreach (var v in nodes)
            {
                subDeg[v] = g.K[v];
                subSize[v] = 1;
                double ext = 0;
                foreach (var (to, w) in g.Adj[v]) if (membership[to] == membership[v]) ext += w;
                subExt[v] = ext;
            }
            var order = nodes.ToArray();
            Shuffle(order, rng);
            foreach (var v in order)
            {
                if (subSize[refined[v]] > 1) continue;   // only still-singleton nodes move
                // node well-connected to C?
                if (subExt[v] < gamma * g.K[v] * (commDegTotal - g.K[v]) / g.TwoM) continue;

                wToSub.Clear();
                foreach (var (to, w) in g.Adj[v])
                    if (membership[to] == membership[v] && refined[to] != refined[v])
                        wToSub[refined[to]] = wToSub.GetValueOrDefault(refined[to]) + w;

                candidates.Clear();
                foreach (var (s, w) in wToSub)
                {
                    // sub-community well-connected to C?
                    if (subExt[s] < gamma * subDeg[s] * (commDegTotal - subDeg[s]) / g.TwoM) continue;
                    double gain = w - gamma * g.K[v] * subDeg[s] / g.TwoM;
                    if (gain > 1e-12) candidates.Add(s);
                }
                if (candidates.Count == 0) continue;
                int target = candidates[rng.Next(candidates.Count)];

                int old = refined[v];
                refined[v] = target;
                subSize[target] += subSize[old];
                subDeg[target] += g.K[v];
                subExt[target] += subExt[old] - 2 * wToSub[target];
                subSize[old] = 0;
            }
            foreach (var v in nodes) { subDeg[v] = 0; subExt[v] = 0; subSize[v] = 0; }
        }
        return refined;
    }

    static Graph Aggregate(Graph g, int[] refined, int refinedCount, out int[] refinedOfNode)
    {
        refinedOfNode = refined;
        var selfW = new double[refinedCount];
        var w = new Dictionary<long, double>();
        long m = 0;
        for (int v = 0; v < g.N; v++)
        {
            int rv = refined[v];
            selfW[rv] += g.SelfW[v];
            foreach (var (to, weight) in g.Adj[v])
            {
                if (to < v) continue;
                int rt = refined[to];
                if (rv == rt) { selfW[rv] += weight; continue; }
                long key = Math.Min(rv, rt) * (long)refinedCount + Math.Max(rv, rt);
                w[key] = w.GetValueOrDefault(key) + weight;
            }
        }
        var counts = new int[refinedCount];
        foreach (var key in w.Keys) { counts[(int)(key / refinedCount)]++; counts[(int)(key % refinedCount)]++; }
        var adj = new (int, double)[refinedCount][];
        for (int v = 0; v < refinedCount; v++) adj[v] = new (int, double)[counts[v]];
        var fill = new int[refinedCount];
        foreach (var (key, weight) in w)
        {
            int a = (int)(key / refinedCount), b = (int)(key % refinedCount);
            adj[a][fill[a]++] = (b, weight);
            adj[b][fill[b]++] = (a, weight);
            m++;
        }
        var agg = new Graph { N = refinedCount, M = m, Adj = adj, SelfW = selfW, K = new double[refinedCount] };
        for (int v = 0; v < refinedCount; v++)
        {
            double k = 2 * selfW[v];
            foreach (var (_, weight) in adj[v]) k += weight;
            agg.K[v] = k;
            agg.TwoM += k;
        }
        return agg;
    }

    static int Renumber(int[] membership)
    {
        var map = new Dictionary<int, int>();
        for (int i = 0; i < membership.Length; i++)
        {
            if (!map.TryGetValue(membership[i], out var id)) map[membership[i]] = id = map.Count;
            membership[i] = id;
        }
        return map.Count;
    }

    static void Shuffle(int[] a, Random rng)
    {
        for (int i = a.Length - 1; i > 0; i--)
        {
            int j = rng.Next(i + 1);
            (a[i], a[j]) = (a[j], a[i]);
        }
    }
}

static class Metrics
{
    // NMI with arithmetic-mean normalization (sklearn default).
    public static double Nmi(int[] a, int[] b)
    {
        int n = a.Length;
        var joint = new Dictionary<(int, int), int>();
        var ca = new Dictionary<int, int>();
        var cb = new Dictionary<int, int>();
        for (int i = 0; i < n; i++)
        {
            joint[(a[i], b[i])] = joint.GetValueOrDefault((a[i], b[i])) + 1;
            ca[a[i]] = ca.GetValueOrDefault(a[i]) + 1;
            cb[b[i]] = cb.GetValueOrDefault(b[i]) + 1;
        }
        double mi = 0;
        foreach (var ((x, y), c) in joint)
        {
            double pxy = (double)c / n, px = (double)ca[x] / n, py = (double)cb[y] / n;
            mi += pxy * Math.Log(pxy / (px * py));
        }
        double ha = 0, hb = 0;
        foreach (var c in ca.Values) { double p = (double)c / n; ha -= p * Math.Log(p); }
        foreach (var c in cb.Values) { double p = (double)c / n; hb -= p * Math.Log(p); }
        if (ha + hb == 0) return 1;
        return 2 * mi / (ha + hb);
    }
}
