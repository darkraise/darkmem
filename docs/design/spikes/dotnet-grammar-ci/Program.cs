using TreeSitter;

// darkmem grammar-CI spike (#14 residual): prove that grammars ABSENT from
// TreeSitter.DotNet's bundle can be self-compiled with `zig cc` (no MSVC, no CMake,
// no tree-sitter CLI) and loaded through the binding's external-library constructor
// `new Language(libraryPath, exportName)` — parse + S-expr query end to end.
//
// Usage: dotnet run -c Release -- <dir-with-self-compiled-win-x64-grammar-dlls>
//        (build the DLLs first with ./build-grammars.sh)

var dir = args.Length > 0 ? args[0] : Environment.GetEnvironmentVariable("GRAMMAR_DIR")
    ?? throw new InvalidOperationException("pass the grammar output dir as arg[0] or GRAMMAR_DIR");

string Lib(string name) => Path.GetFullPath(Path.Combine(dir, $"tree-sitter-{name}.dll"));

Console.WriteLine("=== darkmem grammar-CI spike (self-compiled grammars via zig cc + external load) ===\n");

// (1) regex — the EASY case: pure-generated parser.c, no external scanner
var regex = new Language(Lib("regex"), "tree_sitter_regex");
using var rp = new Parser(regex);
using var rt = rp.Parse("a(b|c)*d")!;
bool regexParseOk = rt.RootNode.Type == "pattern" && !rt.RootNode.HasError;
Console.WriteLine($"[1] regex parse: root='{rt.RootNode.Type}', hasError={rt.RootNode.HasError}");

using var rq = new Query(regex, "(alternation) @alt");
using var rc = rq.Execute(rt.RootNode);
var alts = new List<string>();
foreach (var cap in rc.Captures) if (cap.Name == "alt") alts.Add(cap.Node.Text);
bool regexQueryOk = alts.Count == 1 && alts[0] == "b|c";
Console.WriteLine($"    query (alternation): [{string.Join(", ", alts)}]");

// (2) yaml — the HARD case: hand-written external scanner.c (~52 KB, indentation-
//     significant). Block mappings only parse if the compiled scanner actually works.
var yaml = new Language(Lib("yaml"), "tree_sitter_yaml");
using var yp = new Parser(yaml);
using var yt = yp.Parse("server:\n  host: localhost\n  ports:\n    - 8000\n    - 5433\n")!;
bool yamlParseOk = yt.RootNode.Type == "stream" && !yt.RootNode.HasError;
Console.WriteLine($"[2] yaml parse: root='{yt.RootNode.Type}', hasError={yt.RootNode.HasError}");

using var yq = new Query(yaml, "(block_mapping_pair key: (_) @key)");
using var yc = yq.Execute(yt.RootNode);
var keys = new List<string>();
foreach (var cap in yc.Captures) if (cap.Name == "key") keys.Add(cap.Node.Text);
bool yamlQueryOk = keys.Count == 3 && keys.Contains("server") && keys.Contains("host") && keys.Contains("ports");
Console.WriteLine($"    query block_mapping_pair keys: [{string.Join(", ", keys)}]");

// (3) breadth — ALL 12 missing grammars (14 artifacts: xml→xml+dtd, markdown→block+inline).
//     Load each self-compiled DLL, parse a small valid sample, require an error-free tree.
var breadth = new (string dll, string fn, string sample)[]
{
    ("kotlin", "tree_sitter_kotlin", "fun main() { println(\"hi\") }"),
    ("lua", "tree_sitter_lua", "local x = 1\nprint(x)\n"),
    ("sql", "tree_sitter_sql", "SELECT id, name FROM users WHERE id = 1;"),
    ("zig", "tree_sitter_zig", "const std = @import(\"std\");\n"),
    ("elixir", "tree_sitter_elixir", "defmodule Foo do\n  def bar, do: 1\nend\n"),
    ("cmake", "tree_sitter_cmake", "add_executable(app main.c)\n"),
    ("make", "tree_sitter_make", "all:\n\techo hi\n"),
    ("objc", "tree_sitter_objc", "@interface Foo\n@end\n"),
    ("xml", "tree_sitter_xml", "<?xml version=\"1.0\"?><root><a/></root>"),
    ("dtd", "tree_sitter_dtd", "<!ELEMENT note (#PCDATA)>"),
    ("markdown", "tree_sitter_markdown", "# Title\n\nSome *text*.\n"),
    ("markdown-inline", "tree_sitter_markdown_inline", "Some *emphasis* here"),
};
int breadthOk = 0;
Console.WriteLine("\n[3] breadth: all 12 missing grammars (14 artifacts)");
foreach (var (dll, fn, sample) in breadth)
{
    try
    {
        var lang = new Language(Lib(dll), fn);
        using var parser = new Parser(lang);
        using var tree = parser.Parse(sample)!;
        bool good = !tree.RootNode.HasError;
        if (good) breadthOk++;
        Console.WriteLine($"    {dll,-16} root='{tree.RootNode.Type}' hasError={tree.RootNode.HasError} {(good ? "OK" : "FAIL")}");
    }
    catch (Exception e) { Console.WriteLine($"    {dll,-16} LOAD/PARSE FAILED: {e.Message}"); }
}

// (4) single-DLL grammar pack (optional arg[1] = pack path): every grammar linked into
//     ONE native library, all loaded from that single file — incl. python + c-sharp to
//     prove bundled and unbundled grammars can ship together in one pack.
bool packOk = true;
if (args.Length > 1)
{
    var pack = Path.GetFullPath(args[1]);
    var packLangs = new (string fn, string sample)[]
    {
        ("tree_sitter_kotlin", "fun main() { }"),
        ("tree_sitter_yaml", "a:\n  b: 1\n"),
        ("tree_sitter_sql", "SELECT 1;"),
        ("tree_sitter_markdown", "# T\n"),
        ("tree_sitter_python", "def f():\n    return 1\n"),
        ("tree_sitter_c_sharp", "class A { void F() {} }"),
    };
    int packPass = 0;
    Console.WriteLine($"\n[4] single-DLL pack: {Path.GetFileName(pack)}");
    foreach (var (fn, sample) in packLangs)
    {
        try
        {
            var lang = new Language(pack, fn);
            using var parser = new Parser(lang);
            using var tree = parser.Parse(sample)!;
            bool good = !tree.RootNode.HasError;
            if (good) packPass++;
            Console.WriteLine($"    {fn,-28} root='{tree.RootNode.Type}' hasError={tree.RootNode.HasError} {(good ? "OK" : "FAIL")}");
        }
        catch (Exception e) { Console.WriteLine($"    {fn,-28} LOAD/PARSE FAILED: {e.Message}"); }
    }
    packOk = packPass == packLangs.Length;
    Console.WriteLine($"    pack verdict: {packPass}/{packLangs.Length} languages from ONE file");
}

bool ok = regexParseOk && regexQueryOk && yamlParseOk && yamlQueryOk && breadthOk == breadth.Length && packOk;
Console.WriteLine($"\n[verdict] self-compiled grammars (incl. external scanners) load + parse + query through TreeSitter.DotNet: {(ok ? "WORKS" : "NEEDS REVIEW")} ({breadthOk}/{breadth.Length} breadth)");
Environment.Exit(ok ? 0 : 1);
