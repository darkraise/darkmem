using System.ComponentModel;
using ModelContextProtocol.Server;

// darkmem MCP gap spike (#11 header source-resolution, #12 Host/Origin allowlist):
// real Kestrel host with MapMcp, an endpoint-scoped Host-allowlist middleware returning
// 421, and header resolution via IHttpContextAccessor (the SDK #544 fix pattern).

var builder = WebApplication.CreateBuilder(args);
builder.Logging.ClearProviders();

builder.Services.AddHttpContextAccessor();
builder.Services.AddScoped<ClientContext>();               // (#11) scoped, reads header per request
builder.Services.AddMcpServer()
    .WithHttpTransport(o => o.Stateless = true)
    .WithTools<EchoTools>();                                // proves the SDK hosts tools

var app = builder.Build();

// (#12) endpoint-scoped Host allowlist: localhost always; MCP_ALLOWED_HOSTS extends; foreign -> 421.
var allowed = (Environment.GetEnvironmentVariable("MCP_ALLOWED_HOSTS") ?? "")
    .Split(',', StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries)
    .ToHashSet(StringComparer.OrdinalIgnoreCase);

bool HostAllowed(string host)
{
    if (allowed.Contains("*")) return true;
    if (string.IsNullOrEmpty(host)) return false;
    var bare = host.Split(':')[0].ToLowerInvariant();
    if (bare is "localhost" or "127.0.0.1" or "::1") return true;    // localhost always
    if (allowed.Contains(host) || allowed.Contains(bare)) return true;
    foreach (var a in allowed)                                        // "host:*" wildcard
        if (a.EndsWith(":*") && bare == a[..^2].ToLowerInvariant()) return true;
    return false;
}

app.Use(async (ctx, next) =>
{
    if (ctx.Request.Path.StartsWithSegments("/mcp"))
    {
        var host = ctx.Request.Headers.Host.ToString();
        if (!HostAllowed(host))
        {
            ctx.Response.StatusCode = 421; // Misdirected Request — darkmem's DNS-rebinding defence
            await ctx.Response.WriteAsync("host not allowed");
            return;
        }
    }
    await next();
});

app.MapMcp("/mcp");                                          // the official SDK's streamable-HTTP mount
app.MapGet("/whoami", (ClientContext c) => c.Client);       // exercises #11 header resolution

app.Run("http://127.0.0.1:5199");

// (#11) source resolution: explicit arg > X-Darkmem-Client header > "mcp" default, via IHttpContextAccessor
sealed class ClientContext
{
    public string Client { get; }
    public ClientContext(IHttpContextAccessor acc)
    {
        var h = acc.HttpContext?.Request.Headers["X-Darkmem-Client"].ToString();
        Client = string.IsNullOrEmpty(h) ? "mcp" : h!;
    }
}

[McpServerToolType]
sealed class EchoTools
{
    [McpServerTool, Description("Echo the given text.")]
    public static string Echo(string text) => text;
}
