using System;
using System.Collections.Generic;
using System.Linq;

namespace GraphSpike;

// Weighted undirected graph. Self-loops supported (arise after Louvain aggregation).
sealed class Graph
{
    public readonly int N;
    public readonly List<(int to, double w)>[] Adj;
    public readonly double[] Deg; // weighted degree; self-loop contributes 2w
    public double M2;             // 2m = sum of degrees

    public Graph(int n)
    {
        N = n;
        Adj = new List<(int, double)>[n];
        for (int i = 0; i < n; i++) Adj[i] = new();
        Deg = new double[n];
    }

    public void AddEdge(int u, int v, double w = 1.0)
    {
        if (u == v) { Adj[u].Add((u, w)); Deg[u] += 2 * w; M2 += 2 * w; }
        else { Adj[u].Add((v, w)); Adj[v].Add((u, w)); Deg[u] += w; Deg[v] += w; M2 += 2 * w; }
    }

    public double Modularity(int[] comm, double gamma = 1.0)
    {
        // Q = (1/2m) * Σ_ordered A_ij·δ(ci,cj)  -  γ/(2m)^2 · Σ_c tot_c^2
        double intra = 0;
        for (int i = 0; i < N; i++)
            foreach (var (j, w) in Adj[i])
                if (comm[i] == comm[j]) intra += w;
        var tot = new Dictionary<int, double>();
        for (int i = 0; i < N; i++) tot[comm[i]] = tot.GetValueOrDefault(comm[i]) + Deg[i];
        double degTerm = tot.Values.Sum(t => t * t);
        return intra / M2 - gamma * degTerm / (M2 * M2);
    }
}

static class Louvain
{
    // One level of local moving from singletons to convergence.
    public static int[] LocalMoving(Graph g, double gamma = 1.0)
    {
        int n = g.N;
        var comm = new int[n];
        var tot = new double[n];
        for (int i = 0; i < n; i++) { comm[i] = i; tot[i] = g.Deg[i]; }

        bool improved = true;
        int guard = 0;
        while (improved && guard++ < 1000)
        {
            improved = false;
            for (int i = 0; i < n; i++)
            {
                int ci = comm[i];
                var kin = new Dictionary<int, double>();
                foreach (var (j, w) in g.Adj[i])
                    if (j != i) kin[comm[j]] = kin.GetValueOrDefault(comm[j]) + w;

                tot[ci] -= g.Deg[i]; // remove i from its community

                int best = ci;
                double bestGain = kin.GetValueOrDefault(ci) - gamma * tot[ci] * g.Deg[i] / g.M2;
                foreach (var (c, kic) in kin)
                {
                    double gain = kic - gamma * tot[c] * g.Deg[i] / g.M2;
                    if (gain > bestGain + 1e-12) { bestGain = gain; best = c; }
                }

                comm[i] = best;
                tot[best] += g.Deg[i];
                if (best != ci) improved = true;
            }
        }
        return Relabel(comm);
    }

    // Full multi-level Louvain: local move, aggregate, repeat until Q stops improving.
    public static int[] Detect(Graph g, double gamma = 1.0)
    {
        var node2comm = Enumerable.Range(0, g.N).ToArray();
        var cur = g;
        double lastQ = double.NegativeInfinity;

        while (true)
        {
            var part = LocalMoving(cur, gamma);
            double q = cur.Modularity(part, gamma);
            for (int i = 0; i < node2comm.Length; i++) node2comm[i] = part[node2comm[i]];

            int k = part.Max() + 1;
            if (k == cur.N || q <= lastQ + 1e-9) break; // no coarsening happened
            lastQ = q;
            cur = Aggregate(cur, part, k);
        }
        return Relabel(node2comm);
    }

    static Graph Aggregate(Graph g, int[] part, int k)
    {
        var agg = new Graph(k);
        var acc = new Dictionary<(int, int), double>();
        for (int i = 0; i < g.N; i++)
            foreach (var (j, w) in g.Adj[i])
            {
                if (j < i) continue; // each undirected edge once (i<=j); self-loops i==j once
                int a = part[i], b = part[j];
                var key = a <= b ? (a, b) : (b, a);
                acc[key] = acc.GetValueOrDefault(key) + w;
            }
        foreach (var ((a, b), w) in acc) agg.AddEdge(a, b, w);
        return agg;
    }

    static int[] Relabel(int[] comm)
    {
        var map = new Dictionary<int, int>();
        var outp = new int[comm.Length];
        for (int i = 0; i < comm.Length; i++)
        {
            if (!map.TryGetValue(comm[i], out int id)) { id = map.Count; map[comm[i]] = id; }
            outp[i] = id;
        }
        return outp;
    }
}

static class LeidenRefine
{
    // The property plain Louvain can violate and Leiden guarantees: every community
    // must be internally connected. Split any disconnected community into its
    // connected components (a new community per component).
    public static int[] EnforceConnected(Graph g, int[] comm)
    {
        var outc = new int[g.N];
        Array.Fill(outc, -1);
        int next = 0;
        var byComm = new Dictionary<int, List<int>>();
        for (int i = 0; i < g.N; i++)
        {
            if (!byComm.TryGetValue(comm[i], out var l)) { l = new(); byComm[comm[i]] = l; }
            l.Add(i);
        }

        foreach (var (_, members) in byComm)
        {
            var memberSet = new HashSet<int>(members);
            foreach (var start in members)
            {
                if (outc[start] != -1) continue;
                var queue = new Queue<int>();
                queue.Enqueue(start); outc[start] = next;
                while (queue.Count > 0)
                {
                    int u = queue.Dequeue();
                    foreach (var (v, _) in g.Adj[u])
                        if (v != u && memberSet.Contains(v) && outc[v] == -1) { outc[v] = next; queue.Enqueue(v); }
                }
                next++;
            }
        }
        return outc;
    }
}

static class PageRankAlgo
{
    // Standard PageRank. seed==null => uniform teleport; else personalised (PPR) to seed.
    public static double[] Run(Graph g, double damping = 0.85, int[]? seed = null, int iters = 300, double tol = 1e-12)
    {
        int n = g.N;
        var teleport = new double[n];
        if (seed is { Length: > 0 })
            foreach (var s in seed) teleport[s] = 1.0 / seed.Length;
        else
            for (int i = 0; i < n; i++) teleport[i] = 1.0 / n;

        var r = (double[])teleport.Clone();
        var next = new double[n];
        for (int it = 0; it < iters; it++)
        {
            Array.Clear(next);
            double dangling = 0;
            for (int i = 0; i < n; i++)
            {
                if (g.Deg[i] == 0) { dangling += r[i]; continue; }
                foreach (var (j, w) in g.Adj[i])
                    next[j] += r[i] * (w / g.Deg[i]);
            }
            double diff = 0;
            for (int j = 0; j < n; j++)
            {
                double val = (1 - damping) * teleport[j] + damping * (next[j] + dangling * teleport[j]);
                diff += Math.Abs(val - r[j]);
                next[j] = val;
            }
            (r, next) = (next, r);
            if (diff < tol) break;
        }
        return r;
    }
}

static class Program
{
    static void Main()
    {
        Console.WriteLine("=== darkmem graph deal-breaker spike (pure-managed .NET, no native interop) ===\n");

        // Planted structure: 3 communities of 6 nodes (near-cliques) + 3 thin bridges.
        var g = new Graph(18);
        void Clique(int baseIdx, int size)
        {
            for (int a = 0; a < size; a++)
                for (int b = a + 1; b < size; b++)
                    g.AddEdge(baseIdx + a, baseIdx + b);
        }
        Clique(0, 6); Clique(6, 6); Clique(12, 6);
        g.AddEdge(5, 6);   // A-B bridge
        g.AddEdge(11, 12); // B-C bridge
        g.AddEdge(17, 0);  // C-A bridge

        var planted = new int[18];
        for (int i = 0; i < 18; i++) planted[i] = i / 6;

        var louvain = Louvain.Detect(g);
        var leiden = LeidenRefine.EnforceConnected(g, louvain);

        double qL = g.Modularity(louvain);
        double qLeiden = g.Modularity(leiden);
        int kL = louvain.Max() + 1;
        int kLeiden = leiden.Max() + 1;

        Console.WriteLine($"Planted communities : 3  -> {Show(planted)}");
        Console.WriteLine($"Louvain  communities: {kL}  Q={qL:F4}  -> {Show(louvain)}");
        Console.WriteLine($"Leiden-refined       : {kLeiden}  Q={qLeiden:F4}  -> {Show(leiden)}");

        bool recovered = SamePartition(planted, louvain);
        Console.WriteLine($"\nLouvain recovers planted structure? {(recovered ? "YES" : "NO")}");

        // Force a genuinely disconnected community: drop node 13 (interior of C, not a bridge
        // endpoint) into A's label. A ∪ {13} has no internal path to 13, so Leiden must split it.
        var bad = (int[])louvain.Clone();
        bad[13] = louvain[0];
        var fixedUp = LeidenRefine.EnforceConnected(g, bad);
        int badK = bad.Max() + 1, fixedK = fixedUp.Max() + 1;
        bool splitWorked = fixedK == badK + 1;
        Console.WriteLine($"\nDisconnected-community guarantee (the property plain Louvain lacks):");
        Console.WriteLine($"  bad partition        : {badK} groups (node 13 forced into community A) -> {Show(bad)}");
        Console.WriteLine($"  after Leiden refine  : {fixedK} groups -> {Show(fixedUp)}  (node 13 split back out: {(splitWorked ? "YES" : "NO")})");

        var pr = PageRankAlgo.Run(g);
        var ppr = PageRankAlgo.Run(g, seed: new[] { 0 });
        Console.WriteLine($"\nPageRank  top-5 (global) : {TopK(pr, 5)}");
        Console.WriteLine($"PPR seed=0 top-5         : {TopK(ppr, 5)}  (expect nodes 0-5 = community A)");
        bool pprLocal = TopKIdx(ppr, 5).All(i => i / 6 == 0);
        Console.WriteLine($"PPR concentrates in seed's community? {(pprLocal ? "YES" : "NO")}");

        bool ok = recovered && pprLocal && splitWorked;
        Console.WriteLine($"\n=== VERDICT: pure-managed community detection + PPR {(ok ? "WORKS with NO native dependency" : "NEEDS REVIEW")} ===");
        Environment.Exit(ok ? 0 : 1);
    }

    static string Show(int[] p) => "[" + string.Join(",", p) + "]";

    static bool SamePartition(int[] a, int[] b)
    {
        var map = new Dictionary<int, int>();
        var seen = new HashSet<int>();
        for (int i = 0; i < a.Length; i++)
        {
            if (map.TryGetValue(a[i], out int mapped)) { if (mapped != b[i]) return false; }
            else { if (!seen.Add(b[i])) return false; map[a[i]] = b[i]; }
        }
        return true;
    }

    static string TopK(double[] r, int k) =>
        "[" + string.Join(", ", TopKIdx(r, k).Select(i => $"n{i}:{r[i]:F3}")) + "]";

    static int[] TopKIdx(double[] r, int k) =>
        Enumerable.Range(0, r.Length).OrderByDescending(i => r[i]).Take(k).ToArray();
}
