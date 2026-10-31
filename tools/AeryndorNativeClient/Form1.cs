using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.IO.Pipes;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace AeryndorClient
{
    public class ClientConfig
    {
        public string ServerHost { get; set; } = "207.180.239.190:8090";
        public string ClientMode { get; set; } = "pc_client";
        public string GraphicsPreset { get; set; } = "ultra";
        public int WindowWidth { get; set; } = 1920;
        public int WindowHeight { get; set; } = 1080;
        public bool StartFullscreen { get; set; } = true;
        public string DiscordClientId { get; set; } = "1564764632952995890";
    }

    public class DiscordRpcMessage
    {
        public string details { get; set; } = "";
        public string state { get; set; } = "";
        public string windowTitle { get; set; } = "";
        public string clientId { get; set; } = "";
        public string homepageUrl { get; set; } = "https://aeryndor.ddns.net";
    }

    public class DataPakEntry
    {
        public string p { get; set; } = "";
        public long o { get; set; }
        public int l { get; set; }
        public int z { get; set; }
    }

    public partial class Form1 : Form
    {
        private static readonly byte[] PakSecret = Encoding.UTF8.GetBytes("Aeryndor_Standalone_3D_Engine_Vault_2026_v437!#SecretKey");
        private static readonly HttpClient SharedHttp = CreateHttpClient();
        private readonly ConcurrentDictionary<string, byte[]> memoryVault = new ConcurrentDictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
        private readonly ConcurrentDictionary<string, DataPakEntry> dataPakIndex = new ConcurrentDictionary<string, DataPakEntry>(StringComparer.OrdinalIgnoreCase);
        private string activeDataPakPath = "";
        private long dataPakBodyStartOffset = 0;
        private byte[]? dataPakKeyTable = null;
        private readonly object dataPakReadLock = new object();

        private WebView2 webView;
        private ClientConfig config = new ClientConfig();
        private bool isFullscreen = false;
        private FormBorderStyle prevBorderStyle = FormBorderStyle.Sizable;
        private FormWindowState prevWindowState = FormWindowState.Normal;
        private Rectangle prevBounds;
        private string cachedVaultDir = "";
        private NamedPipeClientStream? discordPipe = null;
        private string connectedDiscordClientId = "";
        private readonly object discordLock = new object();
        private readonly long sessionStartUnix = DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        private static HttpClient CreateHttpClient()
        {
            var c = new HttpClient { Timeout = TimeSpan.FromMinutes(10) };
            c.DefaultRequestHeaders.TryAddWithoutValidation("X-Aeryndor-Vault", "AERYPAK1_CLIENT_2026");
            return c;
        }

        private Task? initialPakLoadTask;

        public Form1()
        {
            LoadConfig();
            InitWindow();
            initialPakLoadTask = Task.Run(() =>
            {
                CleanupLegacyPlaintextPublicFolder();
                LoadEncryptedPakIntoMemory();
                LoadDataPakIndex();
            });
            InitWebViewAsync();
            _ = Task.Run(() => UpdateDiscordRichPresence("🏰 Im Aeryndor Client", "https://aeryndor.ddns.net", config.DiscordClientId));
        }

        private string GetClientBaseDir()
        {
            try
            {
                string? exePath = Environment.ProcessPath;
                if (!string.IsNullOrEmpty(exePath))
                {
                    string? dir = Path.GetDirectoryName(exePath);
                    if (!string.IsNullOrEmpty(dir)) return dir;
                }
            }
            catch { }
            return AppDomain.CurrentDomain.BaseDirectory;
        }

        private void CleanupLegacyPlaintextPublicFolder()
        {
            try
            {
                string appDataPublic = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "AeryndorClient",
                    "public"
                );
                if (Directory.Exists(appDataPublic))
                {
                    Directory.Delete(appDataPublic, true);
                }

                string baseDir = GetClientBaseDir();
                if (!File.Exists(Path.Combine(baseDir, "server", "server.py")))
                {
                    string localPlainPublic = Path.Combine(baseDir, "public");
                    if (Directory.Exists(localPlainPublic))
                    {
                        Directory.Delete(localPlainPublic, true);
                    }
                }
            }
            catch { }
        }

        private string GetEncryptedPackDir()
        {
            if (!string.IsNullOrEmpty(cachedVaultDir)) return cachedVaultDir;
            string appDataPack = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "AeryndorClient",
                "pack"
            );
            Directory.CreateDirectory(appDataPack);
            cachedVaultDir = appDataPack;
            return cachedVaultDir;
        }

        private string GetEnginePakFilePath()
        {
            string baseDir = GetClientBaseDir();
            string[] candidates = new string[]
            {
                Path.Combine(baseDir, "aeryndor_engine.pak"),
                Path.GetFullPath(Path.Combine(baseDir, "..", "aeryndor_engine.pak")),
                Path.Combine(baseDir, "pack", "aeryndor_engine.pak"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AeryndorClient", "aeryndor_engine.pak")
            };
            foreach (string c in candidates)
            {
                if (File.Exists(c)) return c;
            }
            return Path.GetFullPath(Path.Combine(baseDir, "..", "aeryndor_engine.pak"));
        }

        private string GetDataPakFilePath()
        {
            string baseDir = GetClientBaseDir();
            string[] candidates = new string[]
            {
                Path.Combine(baseDir, "aeryndor_data.pak"),
                Path.GetFullPath(Path.Combine(baseDir, "..", "aeryndor_data.pak")),
                Path.Combine(baseDir, "pack", "aeryndor_data.pak"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AeryndorClient", "aeryndor_data.pak")
            };
            foreach (string c in candidates)
            {
                if (File.Exists(c) && new FileInfo(c).Length > 50_000_000) return c;
            }
            return Path.GetFullPath(Path.Combine(baseDir, "..", "aeryndor_data.pak"));
        }

        private static byte[] MakeKeyTable(byte[] salt)
        {
            byte[] kt = new byte[128 * 32];
            using var sha = SHA256.Create();
            byte[] buf = new byte[PakSecret.Length + 16 + 4];
            Buffer.BlockCopy(PakSecret, 0, buf, 0, PakSecret.Length);
            Buffer.BlockCopy(salt, 0, buf, PakSecret.Length, 16);
            for (int i = 0; i < 128; i++)
            {
                byte[] idxBytes = BitConverter.GetBytes((uint)i);
                Buffer.BlockCopy(idxBytes, 0, buf, PakSecret.Length + 16, 4);
                byte[] digest = sha.ComputeHash(buf);
                Buffer.BlockCopy(digest, 0, kt, i * 32, 32);
            }
            return kt;
        }

        private static byte[] CryptWithKeyTable(byte[] data, int offset, int count, byte[] kt)
        {
            byte[] outBytes = new byte[count];
            for (int i = 0; i < count; i++)
            {
                byte maskByte = (byte)((i >> 12) & 0xFF);
                outBytes[i] = (byte)(data[offset + i] ^ kt[i & 4095] ^ maskByte);
            }
            return outBytes;
        }

        private static byte[] CryptPayload(byte[] data, int offset, int count, byte[] salt)
        {
            byte[] kt = MakeKeyTable(salt);
            return CryptWithKeyTable(data, offset, count, kt);
        }

        private static byte[] EncryptSingleBlob(byte[] rawBytes)
        {
            using var sha = SHA256.Create();
            byte[] salt = new byte[16];
            byte[] hash = sha.ComputeHash(rawBytes);
            Buffer.BlockCopy(hash, 0, salt, 0, 16);
            byte[] enc = CryptPayload(rawBytes, 0, rawBytes.Length, salt);
            byte[] result = new byte[8 + 16 + enc.Length];
            Encoding.ASCII.GetBytes("AERYPAK1").CopyTo(result, 0);
            Buffer.BlockCopy(salt, 0, result, 8, 16);
            Buffer.BlockCopy(enc, 0, result, 24, enc.Length);
            return result;
        }

        private static byte[]? DecryptSingleBlob(byte[] pakBytes)
        {
            if (pakBytes == null || pakBytes.Length < 24) return null;
            string magic = Encoding.ASCII.GetString(pakBytes, 0, 8);
            if (magic != "AERYPAK1") return null;
            byte[] salt = new byte[16];
            Buffer.BlockCopy(pakBytes, 8, salt, 0, 16);
            return CryptPayload(pakBytes, 24, pakBytes.Length - 24, salt);
        }

        private static string GetHashedAssetPakName(string relPath)
        {
            using var sha = SHA256.Create();
            byte[] hash = sha.ComputeHash(Encoding.UTF8.GetBytes(relPath.ToLowerInvariant()));
            var sb = new StringBuilder(64);
            for (int i = 0; i < 20; i++) sb.Append(hash[i].ToString("x2"));
            sb.Append(".epak");
            return sb.ToString();
        }

        private bool LoadDataPakIndex()
        {
            try
            {
                string path = GetDataPakFilePath();
                if (!File.Exists(path)) return false;

                using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
                if (fs.Length < 32) return false;

                byte[] header = new byte[28];
                if (fs.Read(header, 0, 28) != 28) return false;
                string magic = Encoding.ASCII.GetString(header, 0, 8);
                if (magic != "AERYPAK2") return false;

                byte[] salt = new byte[16];
                Buffer.BlockCopy(header, 8, salt, 0, 16);
                uint idxLen = BitConverter.ToUInt32(header, 24);
                if (idxLen == 0 || idxLen > 20_000_000 || 28 + idxLen > fs.Length) return false;

                byte[] idxEnc = new byte[idxLen];
                int readTotal = 0;
                while (readTotal < (int)idxLen)
                {
                    int r = fs.Read(idxEnc, readTotal, (int)idxLen - readTotal);
                    if (r <= 0) break;
                    readTotal += r;
                }

                byte[] kt = MakeKeyTable(salt);
                byte[] idxGz = CryptWithKeyTable(idxEnc, 0, idxEnc.Length, kt);
                using var inMs = new MemoryStream(idxGz);
                using var gz = new GZipStream(inMs, CompressionMode.Decompress);
                using var outMs = new MemoryStream();
                gz.CopyTo(outMs);
                string idxJson = Encoding.UTF8.GetString(outMs.ToArray());

                var entries = JsonSerializer.Deserialize<List<DataPakEntry>>(idxJson);
                if (entries == null || entries.Count == 0) return false;

                dataPakIndex.Clear();
                foreach (var entry in entries)
                {
                    if (!string.IsNullOrEmpty(entry.p))
                    {
                        dataPakIndex[entry.p.Replace('\\', '/').TrimStart('/')] = entry;
                    }
                }

                activeDataPakPath = path;
                dataPakBodyStartOffset = 28L + idxLen;
                dataPakKeyTable = kt;
                return true;
            }
            catch
            {
                return false;
            }
        }

        private byte[]? ReadFromLocalDataPak(string relPath)
        {
            if (string.IsNullOrEmpty(activeDataPakPath) || dataPakKeyTable == null) return null;
            if (!dataPakIndex.TryGetValue(relPath, out DataPakEntry? entry) || entry == null) return null;

            try
            {
                byte[] encSlice = new byte[entry.l];
                lock (dataPakReadLock)
                {
                    using var fs = new FileStream(activeDataPakPath, FileMode.Open, FileAccess.Read, FileShare.Read);
                    fs.Seek(dataPakBodyStartOffset + entry.o, SeekOrigin.Begin);
                    int readTotal = 0;
                    while (readTotal < entry.l)
                    {
                        int r = fs.Read(encSlice, readTotal, entry.l - readTotal);
                        if (r <= 0) break;
                        readTotal += r;
                    }
                }

                byte[] decrypted = CryptWithKeyTable(encSlice, 0, encSlice.Length, dataPakKeyTable);
                if (entry.z == 1)
                {
                    using var inMs = new MemoryStream(decrypted);
                    using var gz = new GZipStream(inMs, CompressionMode.Decompress);
                    using var outMs = new MemoryStream();
                    gz.CopyTo(outMs);
                    return outMs.ToArray();
                }
                return decrypted;
            }
            catch
            {
                return null;
            }
        }

        private bool ParseAndLoadEnginePakBytes(byte[] pakBytes)
        {
            try
            {
                byte[]? compressed = DecryptSingleBlob(pakBytes);
                if (compressed == null) return false;

                using var inMs = new MemoryStream(compressed);
                using var gz = new GZipStream(inMs, CompressionMode.Decompress);
                using var outMs = new MemoryStream();
                gz.CopyTo(outMs);
                byte[] rawTable = outMs.ToArray();

                using var br = new BinaryReader(new MemoryStream(rawTable), Encoding.UTF8);
                uint count = br.ReadUInt32();
                for (uint i = 0; i < count; i++)
                {
                    int pathLen = (int)br.ReadUInt32();
                    string relPath = Encoding.UTF8.GetString(br.ReadBytes(pathLen)).Replace('\\', '/').TrimStart('/');
                    int dataLen = (int)br.ReadUInt32();
                    byte[] content = br.ReadBytes(dataLen);
                    memoryVault[relPath] = content;
                }
                return count > 0;
            }
            catch
            {
                return false;
            }
        }

        private void LoadEncryptedPakIntoMemory()
        {
            try
            {
                string pakPath = GetEnginePakFilePath();
                if (File.Exists(pakPath))
                {
                    byte[] rawPak = File.ReadAllBytes(pakPath);
                    ParseAndLoadEnginePakBytes(rawPak);
                }
            }
            catch { }
        }

        private void LoadConfig()
        {
            try
            {
                string baseDir = GetClientBaseDir();
                string cfgPath = Path.Combine(baseDir, "launcher_config.json");
                if (!File.Exists(cfgPath))
                {
                    cfgPath = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                        "AeryndorClient",
                        "launcher_config.json"
                    );
                }
                if (File.Exists(cfgPath))
                {
                    string json = File.ReadAllText(cfgPath);
                    var parsed = JsonSerializer.Deserialize<ClientConfig>(json);
                    if (parsed != null) config = parsed;
                }
            }
            catch { }

            try
            {
                string[] args = Environment.GetCommandLineArgs();
                foreach (string rawArg in args)
                {
                    string a = rawArg?.Trim() ?? "";
                    if (a.Equals("--windowed", StringComparison.OrdinalIgnoreCase))
                    {
                        config.StartFullscreen = false;
                    }
                    else if (a.Equals("--fullscreen", StringComparison.OrdinalIgnoreCase))
                    {
                        config.StartFullscreen = true;
                    }
                    else if (a.StartsWith("--width=", StringComparison.OrdinalIgnoreCase) &&
                             int.TryParse(a.Substring(8), out int wVal) && wVal >= 800)
                    {
                        config.WindowWidth = wVal;
                    }
                    else if (a.StartsWith("--height=", StringComparison.OrdinalIgnoreCase) &&
                             int.TryParse(a.Substring(9), out int hVal) && hVal >= 600)
                    {
                        config.WindowHeight = hVal;
                    }
                    else if (a.StartsWith("--preset=", StringComparison.OrdinalIgnoreCase))
                    {
                        config.GraphicsPreset = a.Substring(9);
                    }
                    else if (a.StartsWith("--host=", StringComparison.OrdinalIgnoreCase))
                    {
                        config.ServerHost = a.Substring(7);
                    }
                }
            }
            catch { }
        }

        private void SaveConfig()
        {
            try
            {
                var opts = new JsonSerializerOptions { WriteIndented = true };
                string json = JsonSerializer.Serialize(config, opts);
                string baseDir = GetClientBaseDir();
                try { File.WriteAllText(Path.Combine(baseDir, "launcher_config.json"), json); } catch { }
                try
                {
                    string appDataDir = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                        "AeryndorClient"
                    );
                    Directory.CreateDirectory(appDataDir);
                    File.WriteAllText(Path.Combine(appDataDir, "launcher_config.json"), json);
                }
                catch { }
            }
            catch { }
        }

        private void InitWindow()
        {
            this.Text = "Aeryndor: Legacy of the Monoliths";
            this.BackColor = Color.FromArgb(8, 12, 20);
            this.StartPosition = FormStartPosition.CenterScreen;

            try
            {
                string? exePath = Environment.ProcessPath;
                if (!string.IsNullOrEmpty(exePath) && File.Exists(exePath))
                {
                    this.Icon = Icon.ExtractAssociatedIcon(exePath);
                }
            }
            catch { }

            string[] args = Environment.GetCommandLineArgs();
            bool directLaunch = Array.Exists(args, a => a.Equals("--direct", StringComparison.OrdinalIgnoreCase));

            if (!directLaunch)
            {
                this.ClientSize = new Size(1040, 640);
                this.MinimumSize = new Size(960, 600);
            }
            else
            {
                ApplyGameWindowGeometry();
            }

            webView = new WebView2
            {
                Dock = DockStyle.Fill,
                DefaultBackgroundColor = Color.FromArgb(8, 12, 20)
            };
            this.Controls.Add(webView);

            this.KeyPreview = true;
            this.KeyDown += Form1_KeyDown;
            this.Resize += (s, e) =>
            {
                if (webView != null) webView.Bounds = this.ClientRectangle;
            };
        }

        private void ApplyGameWindowGeometry()
        {
            Rectangle screen = Screen.PrimaryScreen!.WorkingArea;
            this.MinimumSize = new Size(1024, 600);

            if (config.StartFullscreen)
            {
                this.FormBorderStyle = FormBorderStyle.None;
                this.WindowState = FormWindowState.Normal;
                this.Bounds = Screen.PrimaryScreen.Bounds;
                isFullscreen = true;
            }
            else
            {
                this.FormBorderStyle = FormBorderStyle.Sizable;
                this.ControlBox = true;
                this.MinimizeBox = true;
                this.MaximizeBox = true;
                isFullscreen = false;

                if (config.WindowWidth >= screen.Width)
                {
                    this.WindowState = FormWindowState.Maximized;
                }
                else
                {
                    this.WindowState = FormWindowState.Normal;
                    int maxW = Math.Max(1024, screen.Width - 36);
                    int maxH = Math.Max(640, screen.Height - 44);
                    int targetW = Math.Min(maxW, Math.Max(1024, config.WindowWidth));
                    int targetH = Math.Min(maxH, Math.Max(640, config.WindowHeight));

                    this.Size = new Size(targetW, targetH);
                    this.Location = new Point(
                        screen.Left + Math.Max(0, (screen.Width - this.Width) / 2),
                        screen.Top + Math.Max(0, (screen.Height - this.Height) / 2)
                    );
                }
                prevBorderStyle = FormBorderStyle.Sizable;
                prevWindowState = this.WindowState;
                prevBounds = this.Bounds;
            }
            if (webView != null)
            {
                webView.Bounds = this.ClientRectangle;
            }
        }

        private async void InitWebViewAsync()
        {
            try
            {
                string baseProfileRoot = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "AeryndorClient"
                );
                string dataFolder = Path.Combine(baseProfileRoot, "WebView2Profile");
                Directory.CreateDirectory(dataFolder);

                var options = new CoreWebView2EnvironmentOptions(
                    "--enable-features=VaapiVideoDecoder,CanvasOopRasterization " +
                    "--force_high_performance_gpu --enable-gpu-rasterization --enable-zero-copy --ignore-gpu-blocklist"
                );

                try
                {
                    var env = await CoreWebView2Environment.CreateAsync(null, dataFolder, options);
                    await webView.EnsureCoreWebView2Async(env);
                }
                catch
                {
                    // Falls WebView2Profile durch eine vorherige Instanz oder einen Hintergrund-Prozess (0x800700AA) belegt ist:
                    // Neues WebView2-Control + isoliertes Instanz-Profil verwenden, damit der Start niemals fehlschlägt!
                    try
                    {
                        this.Controls.Remove(webView);
                        webView.Dispose();
                    }
                    catch { }

                    webView = new WebView2
                    {
                        Dock = DockStyle.Fill,
                        DefaultBackgroundColor = Color.FromArgb(8, 12, 20)
                    };
                    this.Controls.Add(webView);

                    string fallbackFolder = Path.Combine(baseProfileRoot, $"WebView2Profile_{Environment.ProcessId}");
                    Directory.CreateDirectory(fallbackFolder);
                    var fallbackEnv = await CoreWebView2Environment.CreateAsync(null, fallbackFolder, options);
                    await webView.EnsureCoreWebView2Async(fallbackEnv);
                }

                webView.CoreWebView2.Settings.AreDevToolsEnabled = false;
                webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                webView.CoreWebView2.Settings.IsStatusBarEnabled = false;
                webView.CoreWebView2.Settings.AreBrowserAcceleratorKeysEnabled = false;
                webView.CoreWebView2.Settings.IsZoomControlEnabled = false;

                try
                {
                    webView.CoreWebView2.Settings.UserAgent = webView.CoreWebView2.Settings.UserAgent + " AeryndorPCClient/4.0";
                }
                catch { }

                // Alle Anfragen an http://client.aeryndor.local/* werden zu 100% lokal aus aeryndor_engine.pak + aeryndor_data.pak bedient!
                webView.CoreWebView2.AddWebResourceRequestedFilter(
                    "http://client.aeryndor.local/*",
                    CoreWebView2WebResourceContext.All
                );
                webView.CoreWebView2.WebResourceRequested += OnWebResourceRequested;

                await webView.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync(
                    $"window.__IS_AERYNDOR_PC_CLIENT__ = true; window.__AERYNDOR_SERVER_HOST__ = '{config.ServerHost}';"
                );

                webView.CoreWebView2.WebMessageReceived += OnWebMessageReceived;
                webView.CoreWebView2.WindowCloseRequested += (s, e) => this.Close();

                string[] args = Environment.GetCommandLineArgs();
                bool directLaunch = Array.Exists(args, a => a.Equals("--direct", StringComparison.OrdinalIgnoreCase));
                if (directLaunch)
                {
                    await SyncEncryptedEnginePakAsync(false);
                    NavigateToGame();
                }
                else
                {
                    webView.CoreWebView2.NavigateToString(BuildLauncherHtml());
                    _ = SyncEncryptedEnginePakAsync(true);
                }

                webView.NavigationCompleted += (s, e) =>
                {
                    webView.Focus();
                };
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "Fehler beim Starten der nativen 3D-Engine:\n" + ex.Message,
                    "Aeryndor Native Client",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        private static string GuessMimeType(string filePath)
        {
            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            return ext switch
            {
                ".html" => "text/html; charset=utf-8",
                ".js" => "application/javascript; charset=utf-8",
                ".css" => "text/css; charset=utf-8",
                ".json" => "application/json; charset=utf-8",
                ".png" => "image/png",
                ".jpg" or ".jpeg" => "image/jpeg",
                ".webp" => "image/webp",
                ".svg" => "image/svg+xml",
                ".ico" => "image/x-icon",
                ".glb" => "model/gltf-binary",
                ".gltf" => "model/gltf+json",
                ".bin" => "application/octet-stream",
                ".mp3" => "audio/mpeg",
                ".wav" => "audio/wav",
                ".ogg" => "audio/ogg",
                _ => "application/octet-stream"
            };
        }

        private static bool IsValidAssetPayload(string relPath, byte[]? data)
        {
            if (data == null || data.Length < 4) return false;
            string ext = Path.GetExtension(relPath).ToLowerInvariant();
            if (ext == ".glb")
            {
                if (data.Length < 28) return false;
                if (data[0] != 0x67 || data[1] != 0x6C || data[2] != 0x54 || data[3] != 0x46) return false;
                uint declaredLen = BitConverter.ToUInt32(data, 8);
                return declaredLen >= 28 && declaredLen <= (uint)data.Length;
            }
            if (ext == ".png")
            {
                return data.Length >= 24 && data[0] == 0x89 && data[1] == 0x50 && data[2] == 0x4E && data[3] == 0x47;
            }
            if (ext == ".jpg" || ext == ".jpeg")
            {
                return data.Length >= 4 && data[0] == 0xFF && data[1] == 0xD8;
            }
            if (ext == ".webp" || ext == ".wav")
            {
                return data.Length >= 12 && data[0] == 0x52 && data[1] == 0x49 && data[2] == 0x46 && data[3] == 0x46;
            }
            if (ext == ".ogg")
            {
                return data.Length >= 14 && data[0] == 0x4F && data[1] == 0x67 && data[2] == 0x67 && data[3] == 0x53;
            }
            // Reject accidental GZIP / AERYPAK1 blobs or HTML error pages for binary assets
            if ((ext == ".bin" || ext == ".mp3" || ext == ".ico") &&
                ((data[0] == 0x1F && data[1] == 0x8B) || (data[0] == 0x3C && data[1] == 0x21)))
            {
                return false;
            }
            return true;
        }

        private async void OnWebResourceRequested(object? sender, CoreWebView2WebResourceRequestedEventArgs e)
        {
            try
            {
                var uri = new Uri(e.Request.Uri);
                if (!uri.Host.Equals("client.aeryndor.local", StringComparison.OrdinalIgnoreCase)) return;

                string relPath = Uri.UnescapeDataString(uri.AbsolutePath).TrimStart('/').Replace('\\', '/');
                if (string.IsNullOrEmpty(relPath)) relPath = "index.html";

                string mime = GuessMimeType(relPath);

                // 1. Aus dem entschlüsselten RAM-Vault (aeryndor_engine.pak) bedienen
                if (memoryVault.TryGetValue(relPath, out byte[]? ramBytes) && ramBytes != null)
                {
                    var ms = new MemoryStream(ramBytes);
                    e.Response = webView.CoreWebView2.Environment.CreateWebResourceResponse(
                        ms, 200, "OK", $"Content-Type: {mime}\r\nCache-Control: no-store, no-cache, must-revalidate\r\nAccess-Control-Allow-Origin: *"
                    );
                    return;
                }

                // 2., 3. & 4. Asynchron im Hintergrund-Thread entschlüsseln/laden, damit der UI-Thread (Fenster-Resize/Maximieren) niemals blockiert!
                CoreWebView2Deferral deferral = e.GetDeferral();
                try
                {
                    if (initialPakLoadTask != null && !initialPakLoadTask.IsCompleted)
                    {
                        await initialPakLoadTask;
                    }

                    if (memoryVault.TryGetValue(relPath, out byte[]? delayedRamBytes) && delayedRamBytes != null)
                    {
                        var ms = new MemoryStream(delayedRamBytes);
                        e.Response = webView.CoreWebView2.Environment.CreateWebResourceResponse(
                            ms, 200, "OK", $"Content-Type: {mime}\r\nCache-Control: no-store, no-cache, must-revalidate\r\nAccess-Control-Allow-Origin: *"
                        );
                        return;
                    }

                    byte[]? pakAssetBytes = await Task.Run(() => ReadFromLocalDataPak(relPath));
                    if (pakAssetBytes != null && IsValidAssetPayload(relPath, pakAssetBytes))
                    {
                        var ms = new MemoryStream(pakAssetBytes);
                        e.Response = webView.CoreWebView2.Environment.CreateWebResourceResponse(
                            ms, 200, "OK", $"Content-Type: {mime}\r\nAccess-Control-Allow-Origin: *"
                        );
                        return;
                    }

                    string epakKey = string.IsNullOrEmpty(uri.Query) ? relPath : $"{relPath}{uri.Query}";
                    string epakFile = Path.Combine(GetEncryptedPackDir(), GetHashedAssetPakName(epakKey));
                    string legacyEpakFile = Path.Combine(GetEncryptedPackDir(), GetHashedAssetPakName(relPath));
                    string? existingEpak = File.Exists(epakFile) ? epakFile : (File.Exists(legacyEpakFile) ? legacyEpakFile : null);
                    if (existingEpak != null)
                    {
                        byte[]? decryptedAsset = await Task.Run(() =>
                        {
                            try { return DecryptSingleBlob(File.ReadAllBytes(existingEpak)); }
                            catch { return null; }
                        });
                        if (decryptedAsset != null && IsValidAssetPayload(relPath, decryptedAsset))
                        {
                            var ms = new MemoryStream(decryptedAsset);
                            e.Response = webView.CoreWebView2.Environment.CreateWebResourceResponse(
                                ms, 200, "OK", $"Content-Type: {mime}\r\nAccess-Control-Allow-Origin: *"
                            );
                            return;
                        }
                        try { File.Delete(existingEpak); } catch { }
                    }

                    string remoteUrl = $"http://{config.ServerHost}{uri.PathAndQuery}";
                    using var resp = await SharedHttp.GetAsync(remoteUrl);
                    if (resp.IsSuccessStatusCode)
                    {
                        byte[] bytes = await resp.Content.ReadAsByteArrayAsync();
                        if (IsValidAssetPayload(relPath, bytes))
                        {
                            _ = Task.Run(() =>
                            {
                                try { File.WriteAllBytes(epakFile, EncryptSingleBlob(bytes)); } catch { }
                            });
                        }

                        string srvMime = resp.Content.Headers.ContentType?.ToString() ?? mime;
                        var ms = new MemoryStream(bytes);
                        e.Response = webView.CoreWebView2.Environment.CreateWebResourceResponse(
                            ms, 200, "OK", $"Content-Type: {srvMime}\r\nAccess-Control-Allow-Origin: *"
                        );
                    }
                }
                catch { }
                finally
                {
                    deferral.Complete();
                }
            }
            catch { }
        }

        private void SendLauncherStatus(string label, int pct, string color = "#86efac")
        {
            try
            {
                if (webView?.CoreWebView2 == null) return;
                string safeLabel = label.Replace("\\", "\\\\").Replace("'", "\\'");
                _ = webView.CoreWebView2.ExecuteScriptAsync(
                    $"if(window.updatePatchStatus) window.updatePatchStatus('{safeLabel}', {pct}, '{color}');"
                );
            }
            catch { }
        }

        private async Task EnsureLocalDataPakDownloadedAsync(bool updateUi)
        {
            if (initialPakLoadTask != null && !initialPakLoadTask.IsCompleted)
            {
                await initialPakLoadTask;
            }
            if (!dataPakIndex.IsEmpty) return;
            if (await Task.Run(() => LoadDataPakIndex())) return;

            try
            {
                string destPath = GetDataPakFilePath();
                string? dir = Path.GetDirectoryName(destPath);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                string tempPath = destPath + ".part";

                string url = $"http://{config.ServerHost}/api/download/data-pak";
                using var resp = await SharedHttp.GetAsync(url, HttpCompletionOption.ResponseHeadersRead);
                if (!resp.IsSuccessStatusCode) return;

                long totalBytes = resp.Content.Headers.ContentLength ?? 241_850_000L;
                long received = 0;
                byte[] buffer = new byte[256 * 1024];

                using (var netStream = await resp.Content.ReadAsStreamAsync())
                using (var fileStream = new FileStream(tempPath, FileMode.Create, FileAccess.Write, FileShare.None))
                {
                    int read;
                    int lastPct = -1;
                    while ((read = await netStream.ReadAsync(buffer, 0, buffer.Length)) > 0)
                    {
                        await fileStream.WriteAsync(buffer, 0, read);
                        received += read;
                        if (updateUi)
                        {
                            int pct = Math.Min(99, (int)Math.Round((received / (double)totalBytes) * 100.0));
                            if (pct != lastPct)
                            {
                                lastPct = pct;
                                double mbDone = received / (1024.0 * 1024.0);
                                double mbTotal = totalBytes / (1024.0 * 1024.0);
                                SendLauncherStatus(
                                    $"Installiere komplettes 3D-Welten-, Objekt- & Texturen-Archiv: {mbDone:0.0} / {mbTotal:0.0} MB ({pct}%)...",
                                    pct,
                                    "#fde047"
                                );
                            }
                        }
                    }
                }

                if (File.Exists(destPath)) File.Delete(destPath);
                File.Move(tempPath, destPath);
                await Task.Run(() => LoadDataPakIndex());
            }
            catch { }
        }

        private async Task SyncEncryptedEnginePakAsync(bool updateUi)
        {
            try
            {
                if (initialPakLoadTask != null && !initialPakLoadTask.IsCompleted)
                {
                    await initialPakLoadTask;
                }
                if (updateUi)
                {
                    SendLauncherStatus("Prüfe verschlüsselten Engine- & Welten-Container...", 15, "#7dd3fc");
                }

                string pakUrl = $"http://{config.ServerHost}/api/client-pack";
                using var resp = await SharedHttp.GetAsync(pakUrl);
                if (resp.IsSuccessStatusCode)
                {
                    byte[] rawPak = await resp.Content.ReadAsByteArrayAsync();
                    await Task.Run(() =>
                    {
                        if (ParseAndLoadEnginePakBytes(rawPak))
                        {
                            try
                            {
                                string basePak = Path.Combine(GetClientBaseDir(), "aeryndor_engine.pak");
                                File.WriteAllBytes(basePak, rawPak);
                            }
                            catch { }
                            try
                            {
                                string parentPak = Path.GetFullPath(Path.Combine(GetClientBaseDir(), "..", "aeryndor_engine.pak"));
                                if (Directory.Exists(Path.GetDirectoryName(parentPak)))
                                {
                                    File.WriteAllBytes(parentPak, rawPak);
                                }
                            }
                            catch { }
                            try
                            {
                                string appPak = Path.Combine(
                                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                    "AeryndorClient",
                                    "aeryndor_engine.pak"
                                );
                                if (Directory.Exists(Path.GetDirectoryName(appPak)))
                                {
                                    File.WriteAllBytes(appPak, rawPak);
                                }
                            }
                            catch { }
                        }
                    });
                }

                // Sicherstellen, dass auch das komplette 3D-Objekte- & Texturen-Archiv (aeryndor_data.pak) lokal vorhanden ist
                await EnsureLocalDataPakDownloadedAsync(updateUi);

                if (updateUi)
                {
                    SendLauncherStatus(
                        $"✓ Kompletter 3D-Client ({dataPakIndex.Count} lokale Objekte, Texturen & Engine) bereit zum Spielen!",
                        100,
                        "#86efac"
                    );
                }
            }
            catch
            {
                if (updateUi)
                {
                    SendLauncherStatus("✓ Lokaler 3D-Client bereit zum Spielen!", 100, "#86efac");
                }
            }
        }

        private async void OnWebMessageReceived(object? sender, CoreWebView2WebMessageReceivedEventArgs e)
        {
            try
            {
                string msg = e.TryGetWebMessageAsString();
                if (string.IsNullOrEmpty(msg)) return;

                if (msg.StartsWith("START_GAME|", StringComparison.OrdinalIgnoreCase))
                {
                    string[] parts = msg.Split('|');
                    if (parts.Length >= 4)
                    {
                        string winMode = parts[1];
                        string preset = parts[2];
                        string host = parts[3];

                        config.GraphicsPreset = preset;
                        if (!string.IsNullOrWhiteSpace(host)) config.ServerHost = host.Trim();

                        if (winMode == "fullscreen")
                        {
                            config.StartFullscreen = true;
                        }
                        else if (winMode == "1600x900")
                        {
                            config.StartFullscreen = false;
                            config.WindowWidth = 1600;
                            config.WindowHeight = 900;
                        }
                        else
                        {
                            config.StartFullscreen = false;
                            config.WindowWidth = 1920;
                            config.WindowHeight = 1080;
                        }
                        SaveConfig();
                    }
                    if (memoryVault.IsEmpty || dataPakIndex.IsEmpty)
                    {
                        await SyncEncryptedEnginePakAsync(false);
                    }
                    ApplyGameWindowGeometry();
                    NavigateToGame();
                }
                else if (msg.StartsWith("SET_WINDOW_MODE|", StringComparison.OrdinalIgnoreCase))
                {
                    string[] parts = msg.Split('|');
                    string mode = parts.Length > 1 ? parts[1].Trim().ToLowerInvariant() : "fullscreen";
                    if (parts.Length > 3 && int.TryParse(parts[2], out int wVal) && int.TryParse(parts[3], out int hVal))
                    {
                        config.WindowWidth = Math.Max(1024, wVal);
                        config.WindowHeight = Math.Max(600, hVal);
                    }
                    config.StartFullscreen = (mode != "windowed");
                    SaveConfig();
                    ApplyGameWindowGeometry();
                }
                else if (msg.StartsWith("DISCORD_RPC|", StringComparison.OrdinalIgnoreCase))
                {
                    string jsonPayload = msg.Substring(12);
                    var rpc = JsonSerializer.Deserialize<DiscordRpcMessage>(jsonPayload);
                    if (rpc != null)
                    {
                        if (!string.IsNullOrWhiteSpace(rpc.windowTitle))
                        {
                            this.Text = rpc.windowTitle;
                        }
                        string effClientId = "1564764632952995890";
                        _ = Task.Run(() => UpdateDiscordRichPresence(rpc.details, rpc.state, effClientId));
                    }
                }
                else if (msg.Equals("TOGGLE_FULLSCREEN", StringComparison.OrdinalIgnoreCase))
                {
                    ToggleFullscreen();
                }
                else if (msg.Equals("CLOSE_LAUNCHER", StringComparison.OrdinalIgnoreCase) ||
                         msg.Equals("QUIT_GAME", StringComparison.OrdinalIgnoreCase))
                {
                    this.Close();
                }
            }
            catch { }
        }

        private async void NavigateToGame()
        {
            try
            {
                if (webView?.CoreWebView2 != null)
                {
                    await webView.CoreWebView2.CallDevToolsProtocolMethodAsync("Network.clearBrowserCache", "{}");
                }
            }
            catch { }

            long ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            string wm = config.StartFullscreen ? "fullscreen" : "windowed";
            string res = $"{config.WindowWidth}x{config.WindowHeight}";
            string targetUrl;
            if (memoryVault.ContainsKey("index.html") || dataPakIndex.ContainsKey("index.html"))
            {
                // Lädt die komplette 3D-Engine + alle 1.149 Objekte/Texturen zu 100% lokal aus aeryndor_engine.pak + aeryndor_data.pak!
                targetUrl = $"http://client.aeryndor.local/index.html?client=pc_client&server={Uri.EscapeDataString(config.ServerHost)}&mode={config.ClientMode}&preset={config.GraphicsPreset}&winmode={wm}&res={res}&_t={ts}";
            }
            else
            {
                targetUrl = $"http://{config.ServerHost}/index.html?client=pc_client&mode={config.ClientMode}&preset={config.GraphicsPreset}&winmode={wm}&res={res}&_t={ts}";
            }
            webView!.CoreWebView2.Navigate(targetUrl);
        }

        private string BuildLauncherHtml()
        {
            string winSel = config.StartFullscreen ? "fullscreen" : (config.WindowWidth == 1600 ? "1600x900" : "1920x1080");
            string presetSel = string.IsNullOrEmpty(config.GraphicsPreset) ? "ultra" : config.GraphicsPreset;
            return @"<!DOCTYPE html>
<html lang=""de"">
<head>
<meta charset=""UTF-8"">
<style>
  * { box-sizing: border-box; user-select: none; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: radial-gradient(circle at 50% 18%, #162844 0%, #09101d 65%, #050811 100%);
    color: #e2e8f0;
    height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 24px 30px;
    border: 1px solid rgba(212, 175, 55, 0.38);
    overflow: hidden;
  }
  .top-row {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  .brand-title {
    font-size: 27px;
    font-weight: 800;
    letter-spacing: 1.5px;
    background: linear-gradient(180deg, #fffbeb 0%, #fde047 45%, #ca8a04 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-transform: uppercase;
  }
  .brand-sub {
    font-size: 12.5px;
    color: #94a3b8;
    margin-top: 3px;
    letter-spacing: 0.5px;
  }
  .srv-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(56, 189, 248, 0.35);
    padding: 7px 14px;
    border-radius: 999px;
    font-size: 12.5px;
    color: #bae6fd;
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #22c55e;
    box-shadow: 0 0 8px #22c55e;
  }
  .mid-grid {
    display: grid;
    grid-template-columns: 1.32fr 1fr;
    gap: 20px;
    margin: 16px 0;
    flex: 1;
    min-height: 0;
  }
  .card {
    background: linear-gradient(180deg, rgba(15, 23, 42, 0.82) 0%, rgba(9, 14, 26, 0.92) 100%);
    border: 1px solid rgba(212, 175, 55, 0.28);
    border-radius: 10px;
    padding: 16px 18px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.55);
  }
  .card-title {
    font-size: 13.5px;
    font-weight: 700;
    color: #fde047;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-bottom: 1px solid rgba(212, 175, 55, 0.22);
    padding-bottom: 8px;
    margin-bottom: 10px;
  }
  .news-list {
    display: flex;
    flex-direction: column;
    gap: 9px;
    font-size: 12.2px;
    line-height: 1.48;
    color: #cbd5e1;
    overflow-y: auto;
  }
  .news-item {
    padding: 8px 11px;
    background: rgba(30, 41, 59, 0.48);
    border-left: 3px solid #eab308;
    border-radius: 4px;
  }
  .news-item b { color: #fef08a; }
  .field {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-bottom: 10px;
  }
  .field label {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 600;
    text-transform: uppercase;
  }
  .field select, .field input {
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid rgba(148, 163, 184, 0.35);
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 12.5px;
    outline: none;
  }
  .bottom-bar {
    display: flex;
    align-items: center;
    gap: 18px;
    background: rgba(9, 14, 26, 0.92);
    border: 1px solid rgba(212, 175, 55, 0.32);
    border-radius: 10px;
    padding: 13px 18px;
  }
  .patch-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .patch-top {
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #cbd5e1;
  }
  .pbar-wrap {
    height: 12px;
    background: #090d16;
    border: 1px solid rgba(212, 175, 55, 0.35);
    border-radius: 999px;
    overflow: hidden;
  }
  .pbar-fill {
    height: 100%;
    width: 25%;
    background: linear-gradient(90deg, #0284c7 0%, #38bdf8 50%, #fde047 100%);
    transition: width 0.2s ease;
  }
  .btn-play {
    background: linear-gradient(180deg, #fde047 0%, #eab308 50%, #a16207 100%);
    color: #090d16;
    font-weight: 800;
    font-size: 14.5px;
    letter-spacing: 1px;
    text-transform: uppercase;
    border: 1px solid #fef08a;
    border-radius: 8px;
    padding: 13px 30px;
    cursor: pointer;
    box-shadow: 0 0 22px rgba(234, 179, 8, 0.45);
  }
</style>
</head>
<body>
  <div class=""top-row"">
    <div>
      <div class=""brand-title"">Aeryndor: Legacy of the Monoliths</div>
      <div class=""brand-sub"">Offizieller Standalone 3D PC-Client (100% Lokale Engine, Objekte &amp; Texturen)</div>
    </div>
    <div class=""srv-pill"">
      <span class=""dot"" id=""srv-dot""></span>
      <span id=""srv-status-txt"">Server 1: Aeryndor (" + config.ServerHost + @") &bull; Online</span>
    </div>
  </div>

  <div class=""mid-grid"">
    <div class=""card"">
      <div class=""card-title"">🔒 Kompletter Lokaler 3D-Client (aeryndor_data.pak)</div>
      <div class=""news-list"">
        <div class=""news-item"">
          <b>Alle 3D-Objekte, Welten &amp; Texturen lokal auf deinem PC</b><br>
          Sämtliche 3D-Modelle, Karten-Geometrien (Hauptstädte, Orktal, Wüste, Eisland, Feuerland), Texturen, Icons und die 3D-Engine liegen verschlüsselt in <code>aeryndor_data.pak</code> direkt auf deiner Festplatte.
        </div>
        <div class=""news-item"">
          <b>Null Nachladen vom Server während des Spielens</b><br>
          Alle Grafikdaten werden direkt lokal von deiner SSD in den Arbeitsspeicher geladen &ndash; vom Server werden nur noch reine Multiplayer-Positionen &amp; Kämpfe übertragen.
        </div>
      </div>
    </div>

    <div class=""card"">
      <div class=""card-title"">⚙️ Client- &amp; Grafik-Optionen</div>
      <div class=""field"">
        <label>Anzeigemodus (F11 im Spiel zum Umschalten)</label>
        <select id=""opt-winmode"">
          <option value=""fullscreen"" " + (winSel == "fullscreen" ? "selected" : "") + @">Randloses Vollbild (Empfohlen)</option>
          <option value=""1920x1080"" " + (winSel == "1920x1080" ? "selected" : "") + @">Fenstermodus (1920 x 1080)</option>
          <option value=""1600x900"" " + (winSel == "1600x900" ? "selected" : "") + @">Fenstermodus (1600 x 900)</option>
        </select>
      </div>
      <div class=""field"">
        <label>Grafik-Pipeline &amp; Qualitätsprofil</label>
        <select id=""opt-preset"">
          <option value=""ultra"" " + (presetSel == "ultra" ? "selected" : "") + @">PC-Client ULTRA (Depth-Water, GTAO, HDR-Bloom, 4K Shadows)</option>
          <option value=""normal"" " + (presetSel == "normal" ? "selected" : "") + @">Ausgewogen / Hoch (90+ FPS)</option>
          <option value=""performance"" " + (presetSel == "performance" ? "selected" : "") + @">Performance / Wettkampf (120+ FPS)</option>
        </select>
      </div>
      <div class=""field"">
        <label>Multiplayer-Server Adresse</label>
        <input type=""text"" id=""opt-host"" value=""" + config.ServerHost + @""" />
      </div>
      <div style=""margin-top:auto;font-size:11.5px;color:#86efac;line-height:1.45;"">
        ✓ Dedizierte Hochleistungs-GPU aktiv<br>
        ✓ Alle 3D-Objekte &amp; Texturen lokal verschlüsselt (.pak)
      </div>
    </div>
  </div>

  <div class=""bottom-bar"">
    <div class=""patch-col"">
      <div class=""patch-top"">
        <span id=""patch-label"">Prüfe lokales 3D-Welten- &amp; Texturen-Archiv (aeryndor_data.pak)...</span>
        <span id=""patch-pct"">15%</span>
      </div>
      <div class=""pbar-wrap"">
        <div class=""pbar-fill"" id=""patch-fill""></div>
      </div>
    </div>
    <button class=""btn-play"" id=""btn-start"">⚔️ SPIEL STARTEN</button>
  </div>

  <script>
    const fill = document.getElementById('patch-fill');
    const pct = document.getElementById('patch-pct');
    const lbl = document.getElementById('patch-label');

    window.updatePatchStatus = function(text, percent, color) {
      lbl.textContent = text;
      if (color) lbl.style.color = color;
      fill.style.width = percent + '%';
      pct.textContent = percent + '%';
    };

    document.getElementById('btn-start').addEventListener('click', () => {
      const wm = document.getElementById('opt-winmode').value;
      const pr = document.getElementById('opt-preset').value;
      const hs = document.getElementById('opt-host').value;
      window.chrome.webview.postMessage('START_GAME|' + wm + '|' + pr + '|' + hs);
    });
  </script>
</body>
</html>";
        }

        private async void Form1_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.F11 || (e.Alt && e.KeyCode == Keys.Enter))
            {
                ToggleFullscreen();
                e.Handled = true;
            }
            else if (e.KeyCode == Keys.F5 && webView?.CoreWebView2 != null)
            {
                try
                {
                    await SyncEncryptedEnginePakAsync(false);
                    NavigateToGame();
                }
                catch { }
                e.Handled = true;
            }
        }

        private void ToggleFullscreen()
        {
            config.StartFullscreen = !isFullscreen;
            SaveConfig();
            ApplyGameWindowGeometry();
        }

        private static void WriteDiscordFrame(Stream pipe, int opcode, string json)
        {
            byte[] payload = Encoding.UTF8.GetBytes(json);
            byte[] header = new byte[8];
            Buffer.BlockCopy(BitConverter.GetBytes(opcode), 0, header, 0, 4);
            Buffer.BlockCopy(BitConverter.GetBytes(payload.Length), 0, header, 4, 4);
            pipe.Write(header, 0, 8);
            pipe.Write(payload, 0, payload.Length);
            pipe.Flush();
        }

        private static void DrainDiscordPipeResponse(Stream pipe)
        {
            byte[] header = new byte[8];
            int r = pipe.Read(header, 0, 8);
            if (r == 8)
            {
                int len = BitConverter.ToInt32(header, 4);
                if (len > 0 && len < 65536)
                {
                    byte[] body = new byte[len];
                    int total = 0;
                    while (total < len)
                    {
                        int n = pipe.Read(body, total, len - total);
                        if (n <= 0) break;
                        total += n;
                    }
                }
            }
        }

        private void UpdateDiscordRichPresence(string details, string state, string clientId)
        {
            if (string.IsNullOrWhiteSpace(clientId)) return;
            lock (discordLock)
            {
                try
                {
                    if (discordPipe == null || !discordPipe.IsConnected || connectedDiscordClientId != clientId)
                    {
                        try { discordPipe?.Dispose(); } catch { }
                        discordPipe = null;

                        for (int i = 0; i < 10; i++)
                        {
                            try
                            {
                                var candidate = new NamedPipeClientStream(".", $"discord-ipc-{i}", PipeDirection.InOut, PipeOptions.None);
                                candidate.Connect(250);
                                string hs = JsonSerializer.Serialize(new { v = 1, client_id = clientId });
                                WriteDiscordFrame(candidate, 0, hs);
                                DrainDiscordPipeResponse(candidate);
                                discordPipe = candidate;
                                connectedDiscordClientId = clientId;
                                break;
                            }
                            catch { }
                        }
                    }

                    if (discordPipe != null && discordPipe.IsConnected)
                    {
                        var frameObj = new
                        {
                            cmd = "SET_ACTIVITY",
                            args = new
                            {
                                pid = Environment.ProcessId,
                                activity = new
                                {
                                    details = string.IsNullOrWhiteSpace(details) ? "⚔️ Spielt Aeryndor" : details,
                                    details_url = "https://aeryndor.ddns.net",
                                    state = string.IsNullOrWhiteSpace(state) || state.Contains("Bereit für Aeryndor", StringComparison.OrdinalIgnoreCase)
                                        ? "https://aeryndor.ddns.net"
                                        : state,
                                    state_url = "https://aeryndor.ddns.net",
                                    timestamps = new { start = sessionStartUnix },
                                    assets = new
                                    {
                                        large_image = "https://cdn.discordapp.com/app-icons/1564764632952995890/d20f0b93a3505c2445e089c47c4f27b2.png?size=512",
                                        large_text = "Aeryndor: Legacy of the Monoliths",
                                        large_url = "https://aeryndor.ddns.net"
                                    },
                                    buttons = new[]
                                    {
                                        new { label = "🌐 Offizielle Homepage", url = "https://aeryndor.ddns.net" },
                                        new { label = "⚡ PC-Client Download", url = "https://aeryndor.ddns.net/download" }
                                    }
                                }
                            },
                            nonce = Guid.NewGuid().ToString("N")
                        };
                        string json = JsonSerializer.Serialize(frameObj);
                        WriteDiscordFrame(discordPipe, 1, json);
                        DrainDiscordPipeResponse(discordPipe);
                    }
                }
                catch
                {
                    try { discordPipe?.Dispose(); } catch { }
                    discordPipe = null;
                }
            }
        }
    }
}
