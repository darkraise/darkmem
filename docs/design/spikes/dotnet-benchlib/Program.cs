using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Npgsql;

// darkmem benchlib spike (#24, the last yellow): rebuild the eval-harness CORE in .NET
// and prove it against the Python original —
//   (1) bench-database lifecycle (benchlib/bench_db.py's reset discipline) via Npgsql
//   (2) the content-hash LLM cache of run_bench.py, REUSING the real Python-built
//       .cache files byte-for-byte (sha256(content + "\x00" + prompt)[:16])
//   (3) the 4-dimension micro P/R/F1 scorer, asserted IDENTICAL to python_reference.py
//       on the real cached LLM outputs vs gold.json (exact tp/fp/fn, F1 to 1e-12).
//
// Run python_reference.py first (writes prompt.txt + reference.json).

var root = Path.GetFullPath(args.Length > 0 ? args[0] : Path.Combine("..", "..", "..", ".."));
var here = Path.GetFullPath(".");
var bench = Path.Combine(root, "backend", "scripts", "extraction_bench");
bool allPass = true;

Console.WriteLine("=== darkmem benchlib spike (.NET harness core vs Python original) ===\n");

// ---- (1) bench-database lifecycle -------------------------------------------------
const string admin = "Host=localhost;Port=5433;Username=darkmem;Password=darkmem;Database=darkmem";
const string benchDbName = "darkmem_bench_spike";
try
{
    await using (var conn = new NpgsqlConnection(admin))
    {
        await conn.OpenAsync();
        await new NpgsqlCommand($"DROP DATABASE IF EXISTS {benchDbName} WITH (FORCE)", conn).ExecuteNonQueryAsync();
        await new NpgsqlCommand($"CREATE DATABASE {benchDbName}", conn).ExecuteNonQueryAsync();
    }
    await using (var conn = new NpgsqlConnection(admin.Replace("Database=darkmem", $"Database={benchDbName}")))
    {
        await conn.OpenAsync();
        // bench_db.py reset discipline: schema drop + re-migrate (migration stand-in DDL;
        // the DbUp chain is the already-green migrations row).
        await new NpgsqlCommand("DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public", conn).ExecuteNonQueryAsync();
        await new NpgsqlCommand("CREATE TABLE memories (id uuid PRIMARY KEY, content text NOT NULL)", conn).ExecuteNonQueryAsync();
        await new NpgsqlCommand("INSERT INTO memories VALUES (gen_random_uuid(), 'bench row')", conn).ExecuteNonQueryAsync();
        var count = (long)(await new NpgsqlCommand("SELECT count(*) FROM memories", conn).ExecuteScalarAsync())!;
        Console.WriteLine($"[1] bench-DB lifecycle: create {benchDbName} -> schema reset -> migrate-stand-in -> rows={count} OK");
    }
    await using (var conn = new NpgsqlConnection(admin))
    {
        await conn.OpenAsync();
        await new NpgsqlCommand($"DROP DATABASE {benchDbName} WITH (FORCE)", conn).ExecuteNonQueryAsync();
    }
}
catch (Exception e) { Console.WriteLine($"[1] bench-DB lifecycle FAILED: {e.Message}"); allPass = false; }

// ---- (2) content-hash cache: reuse the Python-built cache -------------------------
var prompt = File.ReadAllText(Path.Combine(here, "prompt.txt"), new UTF8Encoding(false));
var gold = JsonDocument.Parse(File.ReadAllText(Path.Combine(bench, "gold.json"), Encoding.UTF8))
    .RootElement.GetProperty("memories");

static string CacheKey(string content, string prompt)
{
    var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(content + "\x00" + prompt));
    return Convert.ToHexStringLower(bytes)[..16];
}

int hits = 0, total = 0;
var rawByMem = new Dictionary<string, JsonElement>();
foreach (var g in gold.EnumerateArray())
{
    total++;
    var key = CacheKey(g.GetProperty("content").GetString()!, prompt);
    var cf = Path.Combine(bench, ".cache", key + ".json");
    if (File.Exists(cf))
    {
        hits++;
        rawByMem[g.GetProperty("id").GetString()!] = JsonDocument.Parse(File.ReadAllText(cf, Encoding.UTF8)).RootElement;
    }
}
Console.WriteLine($"[2] cache reuse: {hits}/{total} Python-built cache files hit with .NET-computed keys {(hits == total ? "OK" : "FAIL")}");
if (hits != total) allPass = false;

// write-path round-trip in the same format
var tmpCache = Path.Combine(Path.GetTempPath(), "benchlib-spike-cache");
Directory.CreateDirectory(tmpCache);
var wKey = CacheKey("synthetic bench content", prompt);
File.WriteAllText(Path.Combine(tmpCache, wKey + ".json"), "{\"entities\":[],\"relationships\":[]}", new UTF8Encoding(false));
bool wOk = File.Exists(Path.Combine(tmpCache, wKey + ".json"));
Directory.Delete(tmpCache, true);
Console.WriteLine($"    cache write/read round-trip {(wOk ? "OK" : "FAIL")}");
if (!wOk) allPass = false;

// ---- (3) F1 scorer parity ---------------------------------------------------------
const char Sep = '\x1f';
static string Norm(string? s) => (s ?? "").Trim().ToLowerInvariant();

static HashSet<string> EntKeys(JsonElement ents, bool withType)
{
    var outSet = new HashSet<string>();
    foreach (var e in ents.EnumerateArray())
    {
        var n = Norm(e.TryGetProperty("name", out var nv) ? nv.GetString() : null);
        if (n.Length == 0) continue;
        outSet.Add(withType ? n + Sep + Norm(e.TryGetProperty("type", out var tv) ? tv.GetString() : null) : n);
    }
    return outSet;
}

static HashSet<string> RelKeys(JsonElement rels, bool withType)
{
    var outSet = new HashSet<string>();
    foreach (var r in rels.EnumerateArray())
    {
        var s = Norm(r.TryGetProperty("source", out var sv) ? sv.GetString() : null);
        var t = Norm(r.TryGetProperty("target", out var tv) ? tv.GetString() : null);
        if (s.Length == 0 || t.Length == 0) continue;
        outSet.Add(withType
            ? s + Sep + ((r.TryGetProperty("type", out var yv) ? yv.GetString() : null) ?? "").ToUpperInvariant() + Sep + t
            : s + Sep + t);
    }
    return outSet;
}

static (double P, double R, double F) Prf(int tp, int fp, int fn)
{
    double p = tp + fp > 0 ? (double)tp / (tp + fp) : 0.0;
    double r = tp + fn > 0 ? (double)tp / (tp + fn) : 0.0;
    double f = p + r > 0 ? 2 * p * r / (p + r) : 0.0;
    return (p, r, f);
}

static double F1P(HashSet<string> gs, HashSet<string> ps)
{
    if (gs.Count == 0 && ps.Count == 0) return 1.0;
    int tp = gs.Intersect(ps).Count();
    return Prf(tp, ps.Count - tp, gs.Count - tp).F;
}

var reference = JsonDocument.Parse(File.ReadAllText(Path.Combine(here, "reference.json"), Encoding.UTF8)).RootElement;
var refPerMem = reference.GetProperty("per_memory").EnumerateArray()
    .ToDictionary(e => e.GetProperty("id").GetString()!, e => e);

var dims = new Dictionary<string, int[]>
    { ["ent_nt"] = new int[3], ["ent_n"] = new int[3], ["rel_full"] = new int[3], ["rel_pair"] = new int[3] };
int memMatches = 0;
var empty = JsonDocument.Parse("[]").RootElement;

foreach (var g in gold.EnumerateArray())
{
    var id = g.GetProperty("id").GetString()!;
    if (!rawByMem.TryGetValue(id, out var raw)) continue;
    var pe = raw.TryGetProperty("entities", out var pev) && pev.ValueKind == JsonValueKind.Array ? pev : empty;
    var pr = raw.TryGetProperty("relationships", out var prv) && prv.ValueKind == JsonValueKind.Array ? prv : empty;

    var geNt = EntKeys(g.GetProperty("entities"), true);   var peNt = EntKeys(pe, true);
    var geN = EntKeys(g.GetProperty("entities"), false);   var peN = EntKeys(pe, false);
    var grF = RelKeys(g.GetProperty("relations"), true);   var prF = RelKeys(pr, true);
    var grP = RelKeys(g.GetProperty("relations"), false);  var prP = RelKeys(pr, false);

    foreach (var (dim, gs, ps) in new[] { ("ent_nt", geNt, peNt), ("ent_n", geN, peN), ("rel_full", grF, prF), ("rel_pair", grP, prP) })
    {
        int tp = gs.Intersect(ps).Count();
        dims[dim][0] += tp; dims[dim][1] += ps.Count - tp; dims[dim][2] += gs.Count - tp;
    }

    var re = refPerMem[id];
    bool memOk = Math.Abs(F1P(geNt, peNt) - re.GetProperty("ent_f1").GetDouble()) < 1e-12
              && Math.Abs(F1P(grF, prF) - re.GetProperty("rel_f1").GetDouble()) < 1e-12;
    if (memOk) memMatches++;
    else { Console.WriteLine($"    per-memory MISMATCH at {id}"); allPass = false; }
}

Console.WriteLine($"[3] scorer parity vs python_reference.py (raw cached LLM output vs gold):");
Console.WriteLine($"    per-memory F1s: {memMatches}/{rawByMem.Count} identical (1e-12)");
foreach (var (dim, v) in dims)
{
    var rd = reference.GetProperty("dims").GetProperty(dim);
    bool exact = v[0] == rd.GetProperty("tp").GetInt32() && v[1] == rd.GetProperty("fp").GetInt32() && v[2] == rd.GetProperty("fn").GetInt32();
    var (p, r, f) = Prf(v[0], v[1], v[2]);
    bool fOk = Math.Abs(f - rd.GetProperty("f1").GetDouble()) < 1e-12;
    Console.WriteLine($"    {dim,-9} P={p:F3} R={r:F3} F1={f:F3} (tp={v[0]} fp={v[1]} fn={v[2]}) counts-exact={exact} f1-exact={fOk}");
    if (!exact || !fOk) allPass = false;
}

Console.WriteLine($"\n[verdict] .NET benchlib core (bench-DB lifecycle + cache reuse + scorer parity): {(allPass ? "PASS" : "FAIL")}");
Environment.Exit(allPass ? 0 : 1);
