using TreeSitter;

// darkmem tree-sitter gap spike (#13): prove TreeSitter.DotNet parses multiple bundled
// languages and runs S-expression queries with captures — the exact code-indexing core.

Console.WriteLine("=== darkmem tree-sitter gap spike (TreeSitter.DotNet 1.3.0, bundled grammars) ===\n");

static Language LoadLang(string name)
{
    foreach (var id in new[] { name, name.Replace('-', '_'), name.Replace('_', '-') })
        try { return new Language(id); } catch { /* try next id form */ }
    throw new InvalidOperationException($"could not load grammar '{name}'");
}

static List<string> Query(Language lang, string src, string sexpr, string capture)
{
    using var parser = new Parser(lang);
    using var tree = parser.Parse(src);
    var root = tree.RootNode;
    using var query = new Query(lang, sexpr);
    using var cursor = query.Execute(root);
    var names = new List<string>();
    foreach (var cap in cursor.Captures)
        if (cap.Name == capture) names.Add(cap.Node.Text);
    return names;
}

// (1) C# — extract method names
var cs = LoadLang("c_sharp");
var csMethods = Query(cs, "class A { void Foo() {} int Bar() => 1; }",
    "(method_declaration name: (identifier) @name)", "name");
Console.WriteLine($"[1] C# method_declaration names: [{string.Join(", ", csMethods)}]");
bool csOk = csMethods.SequenceEqual(new[] { "Foo", "Bar" });

// (2) Python — extract function names (multi-language proof)
var py = LoadLang("python");
var pyFns = Query(py, "def foo():\n    pass\ndef bar(x):\n    return x\n",
    "(function_definition name: (identifier) @fn)", "fn");
Console.WriteLine($"[2] Python function_definition names: [{string.Join(", ", pyFns)}]");
bool pyOk = pyFns.SequenceEqual(new[] { "foo", "bar" });

// (3) PHP — the documented multi-entrypoint quirk (language_php in Python) is just a name here
bool phpOk;
try
{
    var php = LoadLang("php");
    using var parser = new Parser(php);
    using var tree = parser.Parse("<?php function greet($n) { return \"hi $n\"; }");
    var root = tree.RootNode;
    phpOk = !root.HasError && root.Type == "program";
    Console.WriteLine($"[3] PHP parse: root type='{root.Type}', hasError={root.HasError} (the language_php quirk is a non-issue here)");
}
catch (Exception e) { phpOk = false; Console.WriteLine($"[3] PHP parse FAILED: {e.Message}"); }

// (4) Query predicates are exposed (capture + predicate parity the memo wanted verified)
using var predParser = new Parser(cs);
using var predTree = predParser.Parse("class A { void Foo() {} void Bar() {} }");
using var predQuery = new Query(cs, "((method_declaration name: (identifier) @m) (#eq? @m \"Foo\"))");
using var predCursor = predQuery.Execute(predTree.RootNode);
int predCaps = 0; bool predMetaPresent = false;
foreach (var cap in predCursor.Captures) { predCaps++; if (cap.UserPredicates is not null) predMetaPresent = true; }
Console.WriteLine($"[4] predicate query executed ({predCaps} raw captures); #eq? predicate metadata exposed on captures? {predMetaPresent}");

bool ok = csOk && pyOk && phpOk && predMetaPresent;
Console.WriteLine($"\n[verdict] tree-sitter core binding (parse + S-expr query + captures + predicate metadata) across bundled grammars: {(ok ? "WORKS" : "NEEDS REVIEW")}");
Console.WriteLine("[note] 12 of darkmem's 33 grammars are NOT bundled (kotlin, lua, yaml, sql, zig, elixir, xml, regex, cmake, make, objc, markdown) — those still need a per-RID self-compile pipeline (gap #14).");
Environment.Exit(ok ? 0 : 1);
