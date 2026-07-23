using System.Text.RegularExpressions;
using Npgsql;
using Pgvector;
using Pgvector.Npgsql;

// darkmem data-layer gap spike: prove Npgsql + pgvector do the exact things darkmem's
// Postgres surface needs — runtime per-fingerprint child-table DDL with a sanitised slug,
// a vector insert with NO CAST wrapper, and the 1-(embedding <=> :v) cosine query — live.

const string connStr = "Host=127.0.0.1;Port=5433;Username=darkmem;Password=darkmem;Database=darkmem";

Console.WriteLine("=== darkmem data-layer gap spike (Npgsql + pgvector, live dev Postgres) ===\n");

// (1) Slug sanitisation is the security invariant for interpolated child-table names.
static string SanitiseSlug(string raw)
{
    if (!Regex.IsMatch(raw, "^[a-z0-9_]+$"))
        throw new ArgumentException($"unsafe fingerprint slug rejected: '{raw}'");
    return raw;
}

// prove a malicious slug is rejected (identifiers cannot be parameterised, so this gate matters)
bool rejected = false;
try { SanitiseSlug("evil\"; DROP TABLE memories;--"); }
catch (ArgumentException) { rejected = true; }
Console.WriteLine($"[1] slug sanitisation rejects injection attempt? {(rejected ? "YES" : "NO")}");

var dsb = new NpgsqlDataSourceBuilder(connStr);
dsb.UseVector(); // registers the pgvector type mapping — this is what removes the need for CAST
await using var ds = dsb.Build();

// (2) runtime per-fingerprint child table DDL (the pattern EF migrations cannot express)
string slug = SanitiseSlug("spike_test_9c1f");
string table = $"memory_embeddings__{slug}";
await using (var ddl = ds.CreateCommand(
    $"CREATE TABLE IF NOT EXISTS {table} (id uuid PRIMARY KEY, embedding vector(4))"))
    await ddl.ExecuteNonQueryAsync();
Console.WriteLine($"[2] runtime child table created: {table}");

try
{
    // (3) insert vectors binding a Vector parameter directly — NO CAST(:v AS vector) needed
    var rows = new (Guid id, float[] vec)[]
    {
        (Guid.NewGuid(), new float[] {1f, 0f, 0f, 0f}),
        (Guid.NewGuid(), new float[] {0.9f, 0.1f, 0f, 0f}),
        (Guid.NewGuid(), new float[] {0f, 1f, 0f, 0f}),
        (Guid.NewGuid(), new float[] {0f, 0f, 0f, 1f}),
    };
    foreach (var (id, vec) in rows)
    {
        await using var ins = ds.CreateCommand($"INSERT INTO {table} (id, embedding) VALUES ($1, $2)");
        ins.Parameters.AddWithValue(id);
        ins.Parameters.AddWithValue(new Vector(vec)); // bound as vector, no cast
        await ins.ExecuteNonQueryAsync();
    }
    Console.WriteLine($"[3] inserted {rows.Length} embeddings with NO CAST wrapper (Npgsql resolved the type)");

    // (4) cosine query: 1 - (embedding <=> :q), ordered by nearest — the exact darkmem shape
    var query = new Vector(new float[] {1f, 0f, 0f, 0f}); // nearest to row 0, then row 1
    await using var sel = ds.CreateCommand(
        $"SELECT id, 1 - (embedding <=> $1) AS sim FROM {table} ORDER BY embedding <=> $1 LIMIT 3");
    sel.Parameters.AddWithValue(query);
    await using var reader = await sel.ExecuteReaderAsync();
    Console.WriteLine("[4] cosine query 1-(embedding <=> $1) top-3:");
    int n = 0; double topSim = -1;
    while (await reader.ReadAsync())
    {
        double sim = reader.GetDouble(1);
        if (n == 0) topSim = sim;
        Console.WriteLine($"      {reader.GetGuid(0)}  sim={sim:F4}");
        n++;
    }
    bool cosineOk = n == 3 && topSim > 0.999; // exact match to query => sim ~1.0
    Console.WriteLine($"\n[verdict] Npgsql + pgvector round-trip (runtime DDL + no-CAST insert + cosine): "
        + $"{(rejected && cosineOk ? "WORKS" : "NEEDS REVIEW")}");
    Environment.Exit(rejected && cosineOk ? 0 : 1);
}
finally
{
    await using var drop = ds.CreateCommand($"DROP TABLE IF EXISTS {table}");
    await drop.ExecuteNonQueryAsync();
    Console.WriteLine($"[cleanup] dropped {table}");
}
