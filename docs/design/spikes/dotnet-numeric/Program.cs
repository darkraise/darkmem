using MathNet.Numerics.LinearAlgebra;

// darkmem numeric-core gap spike: the "hidden" dependency inside the vector repo —
// DBSCAN clustering, vectorised cosine-similarity matrices, and 2-D eigen-projection
// of the memory graph. Prove all three run in .NET (hand-rolled DBSCAN + MathNet eigen).

Console.WriteLine("=== darkmem numeric-core gap spike (DBSCAN + cosine + eigen) ===\n");

// Three well-separated clusters in 5-D + 2 noise points (18 pts total).
var rng = new Random(42);
var pts = new List<double[]>();
var truth = new List<int>();
double[][] centers = {
    new[] {5.0, 0, 0, 0, 0}, new[] {0.0, 5, 0, 0, 0}, new[] {0.0, 0, 0, 5, 5},
};
for (int c = 0; c < 3; c++)
    for (int k = 0; k < 5; k++)
    {
        var p = (double[])centers[c].Clone();
        for (int d = 0; d < 5; d++) p[d] += (rng.NextDouble() - 0.5) * 0.4;
        pts.Add(p); truth.Add(c);
    }
pts.Add(new[] {9.0, 9, 9, 0, 0}); truth.Add(-1); // noise
pts.Add(new[] {-8.0, 3, -7, 2, 0}); truth.Add(-1); // noise
int N = pts.Count;

// (1) vectorised cosine-similarity matrix
static double Dot(double[] a, double[] b) { double s = 0; for (int i = 0; i < a.Length; i++) s += a[i] * b[i]; return s; }
static double Norm(double[] a) => Math.Sqrt(Dot(a, a));
double Cos(int i, int j) => Dot(pts[i], pts[j]) / (Norm(pts[i]) * Norm(pts[j]) + 1e-12);
var sim = Matrix<double>.Build.Dense(N, N, (i, j) => Cos(i, j));
Console.WriteLine($"[1] cosine-similarity matrix {N}x{N} built (sample sim[0,1]={sim[0, 1]:F3}, sim[0,5]={sim[0, 5]:F3})");

// (2) DBSCAN over cosine DISTANCE (1 - cosine), hand-rolled (~50 LOC — the no-drop-in part)
int[] Dbscan(double eps, int minPts)
{
    var label = new int[N]; Array.Fill(label, -2); // -2 unvisited, -1 noise, >=0 cluster
    int cid = 0;
    List<int> Region(int p)
    {
        var r = new List<int>();
        for (int q = 0; q < N; q++) if (1.0 - Cos(p, q) <= eps) r.Add(q);
        return r;
    }
    for (int p = 0; p < N; p++)
    {
        if (label[p] != -2) continue;
        var neigh = Region(p);
        if (neigh.Count < minPts) { label[p] = -1; continue; }
        label[p] = cid;
        var seeds = new Queue<int>(neigh.Where(q => q != p));
        while (seeds.Count > 0)
        {
            int q = seeds.Dequeue();
            if (label[q] == -1) label[q] = cid;
            if (label[q] != -2) continue;
            label[q] = cid;
            var qn = Region(q);
            if (qn.Count >= minPts) foreach (var x in qn) seeds.Enqueue(x);
        }
        cid++;
    }
    return label;
}
var dbscan = Dbscan(eps: 0.15, minPts: 3);
int clusters = dbscan.Where(l => l >= 0).Distinct().Count();
int noise = dbscan.Count(l => l == -1);
Console.WriteLine($"[2] DBSCAN found {clusters} clusters, {noise} noise points -> {string.Join(",", dbscan)}");
// each planted cluster must map to exactly one DBSCAN label; the 2 noise pts must be noise
bool clustersOk = clusters == 3 && noise == 2 &&
    Enumerable.Range(0, 3).All(c => dbscan.Where((_, i) => truth[i] == c).Distinct().Count() == 1);

// (3) 2-D eigen-projection: top-2 eigenvectors of the (symmetric) similarity matrix (MathNet EVD)
var evd = sim.Evd(Symmetricity.Symmetric);
var eigVals = evd.EigenValues.Select(z => z.Real).ToArray();
var order = Enumerable.Range(0, N).OrderByDescending(i => eigVals[i]).Take(2).ToArray();
var proj = Matrix<double>.Build.Dense(N, 2, (i, k) => evd.EigenVectors[i, order[k]]);
bool eigOk = proj.Enumerate().All(double.IsFinite) && !double.IsNaN(eigVals[order[0]]);
Console.WriteLine($"[3] MathNet eigen-decomposition OK; top-2 eigenvalues=({eigVals[order[0]]:F2},{eigVals[order[1]]:F2}); "
    + $"2-D projection[0]=({proj[0, 0]:F3},{proj[0, 1]:F3})");

bool ok = clustersOk && eigOk;
Console.WriteLine($"\n[verdict] numeric core (DBSCAN + cosine matrix + eigen-projection) in .NET: {(ok ? "WORKS" : "NEEDS REVIEW")}");
Environment.Exit(ok ? 0 : 1);
