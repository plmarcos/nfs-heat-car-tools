using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using FrostySdk;
using FrostySdk.Interfaces;
using FrostySdk.Managers;
using FrostySdk.Resources;
using MeshSetPlugin.Resources;
using TexturePlugin;

namespace HeatTool
{
    public class SimpleLogger : ILogger
    {
        public void Log(string t, params object[] v) { }
        public void LogError(string t, params object[] v) { }
        public void LogWarning(string t, params object[] v) { }
    }

    public static class Boot
    {
        public static FileSystem Fs;
        public static AssetManager Am;
        static readonly CultureInfo IC = CultureInfo.InvariantCulture;

        public static string Init(string profileKey, string gameDir, string keyPath)
        {
            ProfilesLibrary.Initialize(new List<Profile>());
            ProfilesLibrary.Initialize(profileKey);
            var log = new SimpleLogger();
            if (ProfilesLibrary.RequiresKey)
            {
                byte[] kd = File.ReadAllBytes(keyPath);
                byte[] k1 = new byte[0x10]; Array.Copy(kd, k1, 0x10);
                KeyManager.Instance.AddKey("Key1", k1);
            }
            Fs = new FileSystem(gameDir);
            foreach (FileSystemSource s in ProfilesLibrary.Sources) Fs.AddSource(s.Path, s.SubDirs);
            Fs.Initialize(ProfilesLibrary.RequiresKey ? KeyManager.Instance.GetKey("Key1") : null);
            // true = actually load the EbxClasses SDK; with false the enum lookups
            // used by the texture exporter (RenderFormat, TextureType) return null.
            TypeLibrary.Initialize(true);
            var rm = new ResourceManager(Fs); rm.SetLogger(log); rm.Initialize();
            Am = new AssetManager(Fs, rm); Am.SetLogger(log); Am.Initialize(false, null);
            return "OK " + ProfilesLibrary.ProfileName + " dv=" + ProfilesLibrary.DataVersion;
        }

        // ---- list every mesh ebx under a vehicle folder ----
        public static string[] ListVehicleFolders()
        {
            var set = new SortedSet<string>(StringComparer.Ordinal);
            foreach (EbxAssetEntry e in Am.EnumerateEbx(""))
            {
                if (e.Type == null || !e.Type.Contains("MeshAsset")) continue;
                if (!e.Name.StartsWith("vehicles/player/")) continue;
                string rest = e.Name.Substring("vehicles/player/".Length);
                int i = rest.IndexOf('/');
                if (i > 0) set.Add(rest.Substring(0, i));
            }
            return set.ToArray();
        }

        public static string[] ListMeshes(string carFolder)
        {
            string pre = "vehicles/player/" + carFolder + "/";
            var l = new List<string>();
            foreach (EbxAssetEntry e in Am.EnumerateEbx(""))
            {
                if (e.Type == null || !e.Type.Contains("MeshAsset")) continue;
                if (e.Name.StartsWith(pre)) l.Add(e.Name);
            }
            l.Sort(StringComparer.Ordinal);
            return l.ToArray();
        }

        static float Half(ushort h)
        {
            int s = (h >> 15) & 0x1, e = (h >> 10) & 0x1F, m = h & 0x3FF;
            if (e == 0) { if (m == 0) return 0f; return (float)((s == 1 ? -1 : 1) * Math.Pow(2, -14) * (m / 1024.0)); }
            if (e == 31) return 0f;
            return (float)((s == 1 ? -1 : 1) * Math.Pow(2, e - 15) * (1 + m / 1024.0));
        }

        struct V { public float X, Y, Z, U, W; }

        static float[] ReadElem(byte[] b, int at, VertexElementFormat f, out int comps)
        {
            switch (f)
            {
                case VertexElementFormat.Float: comps = 1; return new float[] { BitConverter.ToSingle(b, at) };
                case VertexElementFormat.Float2: comps = 2; return new float[] { BitConverter.ToSingle(b, at), BitConverter.ToSingle(b, at + 4) };
                case VertexElementFormat.Float3: comps = 3; return new float[] { BitConverter.ToSingle(b, at), BitConverter.ToSingle(b, at + 4), BitConverter.ToSingle(b, at + 8) };
                case VertexElementFormat.Float4: comps = 4; return new float[] { BitConverter.ToSingle(b, at), BitConverter.ToSingle(b, at + 4), BitConverter.ToSingle(b, at + 8), BitConverter.ToSingle(b, at + 12) };
                case VertexElementFormat.Half: comps = 1; return new float[] { Half(BitConverter.ToUInt16(b, at)) };
                case VertexElementFormat.Half2: comps = 2; return new float[] { Half(BitConverter.ToUInt16(b, at)), Half(BitConverter.ToUInt16(b, at + 2)) };
                case VertexElementFormat.Half3: comps = 3; return new float[] { Half(BitConverter.ToUInt16(b, at)), Half(BitConverter.ToUInt16(b, at + 2)), Half(BitConverter.ToUInt16(b, at + 4)) };
                case VertexElementFormat.Half4: comps = 4; return new float[] { Half(BitConverter.ToUInt16(b, at)), Half(BitConverter.ToUInt16(b, at + 2)), Half(BitConverter.ToUInt16(b, at + 4)), Half(BitConverter.ToUInt16(b, at + 6)) };
                case VertexElementFormat.Short2N: comps = 2; return new float[] { BitConverter.ToInt16(b, at) / 32767f, BitConverter.ToInt16(b, at + 2) / 32767f };
                case VertexElementFormat.Short4N: comps = 4; return new float[] { BitConverter.ToInt16(b, at) / 32767f, BitConverter.ToInt16(b, at + 2) / 32767f, BitConverter.ToInt16(b, at + 4) / 32767f, BitConverter.ToInt16(b, at + 6) / 32767f };
                case VertexElementFormat.Short2: comps = 2; return new float[] { (float)BitConverter.ToInt16(b, at), (float)BitConverter.ToInt16(b, at + 2) };
                case VertexElementFormat.Short4: comps = 4; return new float[] { (float)BitConverter.ToInt16(b, at), (float)BitConverter.ToInt16(b, at + 2), (float)BitConverter.ToInt16(b, at + 4), (float)BitConverter.ToInt16(b, at + 6) };
                case VertexElementFormat.UShort2N: comps = 2; return new float[] { BitConverter.ToUInt16(b, at) / 65535f, BitConverter.ToUInt16(b, at + 2) / 65535f };
                case VertexElementFormat.UShort4N: comps = 4; return new float[] { BitConverter.ToUInt16(b, at) / 65535f, BitConverter.ToUInt16(b, at + 2) / 65535f, BitConverter.ToUInt16(b, at + 4) / 65535f, BitConverter.ToUInt16(b, at + 6) / 65535f };
                case VertexElementFormat.Byte4N: comps = 4; return new float[] { (sbyte)b[at] / 127f, (sbyte)b[at + 1] / 127f, (sbyte)b[at + 2] / 127f, (sbyte)b[at + 3] / 127f };
                case VertexElementFormat.UByte4N: comps = 4; return new float[] { b[at] / 255f, b[at + 1] / 255f, b[at + 2] / 255f, b[at + 3] / 255f };
                default: comps = 0; return null;
            }
        }

        class Acc
        {
            public StringBuilder Obj = new StringBuilder();
            public HashSet<string> Mats = new HashSet<string>();
            public int VBase = 1;
            public int Tris = 0;
            public int Sections = 0;
            public HashSet<string> Warn = new HashSet<string>();
        }

        // Appends one mesh asset's LOD into the accumulator. Returns false if nothing usable.
        static bool AppendMesh(Acc acc, string meshName, string objectName, int lodIndex, bool onlyRenderable)
        {
            ResAssetEntry res = Am.GetResEntry(meshName);
            if (res == null) { acc.Warn.Add("nores:" + objectName); return false; }
            MeshSet ms;
            try { ms = Am.GetResAs<MeshSet>(res, null); }
            catch (Exception ex) { acc.Warn.Add("read:" + objectName + ":" + ex.GetType().Name); return false; }
            if (ms.Lods.Count == 0) return false;
            int li = lodIndex < ms.Lods.Count ? lodIndex : 0;
            MeshSetLod lod = ms.Lods[li];

            byte[] buf;
            try
            {
                if (lod.ChunkId != Guid.Empty)
                {
                    ChunkAssetEntry ce = Am.GetChunkEntry(lod.ChunkId);
                    if (ce == null) { acc.Warn.Add("nochunk:" + objectName); return false; }
                    using (Stream st = Am.GetChunk(ce))
                    using (var mm = new MemoryStream()) { st.CopyTo(mm); buf = mm.ToArray(); }
                }
                else if (lod.InlineData != null && lod.InlineData.Length > 0) buf = lod.InlineData;
                else return false;
            }
            catch (Exception ex) { acc.Warn.Add("chunk:" + objectName + ":" + ex.GetType().Name); return false; }

            long totalIdx = 0;
            foreach (MeshSetSection s in lod.Sections) totalIdx += s.PrimitiveCount * 3;
            int idxSize = 2;
            if (totalIdx > 0 && (lod.IndexBufferSize / (double)totalIdx) >= 3.0) idxSize = 4;
            long ibBase = lod.VertexBufferSize;

            var seen = new HashSet<string>();   // dedupe aliased sections
            bool wroteObject = false;
            int localSec = 0;

            foreach (MeshSetSection sec in lod.Sections)
            {
                bool renderable;
                try { renderable = lod.IsSectionRenderable(sec); } catch { renderable = true; }
                if (onlyRenderable && !renderable) continue;
                if (sec.VertexCount == 0 || sec.PrimitiveCount == 0) continue;

                string key = sec.VertexOffset + "|" + sec.StartIndex + "|" + sec.VertexCount + "|" + sec.PrimitiveCount;
                if (!seen.Add(key)) continue;

                var decl = sec.GeometryDeclDesc[0];
                var streamBase = new long[decl.Streams.Length];
                long cur = sec.VertexOffset;
                for (int j = 0; j < decl.Streams.Length; j++)
                {
                    streamBase[j] = cur;
                    cur += (long)sec.VertexCount * decl.Streams[j].VertexStride;
                }

                var verts = new V[sec.VertexCount];
                bool gotPos = false, gotUv = false;

                foreach (var e in decl.Elements)
                {
                    if (e.Usage == VertexElementUsage.Unknown) continue;
                    if (e.StreamIndex >= decl.Streams.Length) continue;
                    int stride = decl.Streams[e.StreamIndex].VertexStride;
                    if (stride == 0) continue;
                    bool isPos = (e.Usage == VertexElementUsage.Pos || e.Usage == VertexElementUsage.PosAndScale);
                    bool isUv = (e.Usage == VertexElementUsage.TexCoord0);
                    if (!isPos && !isUv) continue;

                    for (int i = 0; i < sec.VertexCount; i++)
                    {
                        long at = streamBase[e.StreamIndex] + (long)i * stride + e.Offset;
                        if (at < 0 || at + e.Size > buf.Length) { acc.Warn.Add("oob"); break; }
                        int comps;
                        float[] vals = ReadElem(buf, (int)at, e.Format, out comps);
                        if (vals == null) { acc.Warn.Add("fmt:" + e.Format); break; }
                        if (isPos && comps >= 3) { verts[i].X = vals[0]; verts[i].Y = vals[1]; verts[i].Z = vals[2]; gotPos = true; }
                        else if (isUv && comps >= 2) { verts[i].U = vals[0]; verts[i].W = vals[1]; gotUv = true; }
                    }
                }
                if (!gotPos) continue;

                if (!wroteObject) { acc.Obj.AppendLine("o " + objectName); wroteObject = true; }

                string mat = string.IsNullOrEmpty(sec.Name) ? ("mat_" + sec.MaterialId) : sec.Name;
                mat = Sanitize(mat);
                acc.Mats.Add(mat);
                acc.Obj.AppendLine("g " + objectName + "_" + localSec + "_" + mat);
                acc.Obj.AppendLine("usemtl " + mat);

                for (int i = 0; i < verts.Length; i++)
                    acc.Obj.AppendLine("v " + verts[i].X.ToString("0.######", IC) + " " + verts[i].Y.ToString("0.######", IC) + " " + verts[i].Z.ToString("0.######", IC));
                if (gotUv)
                    for (int i = 0; i < verts.Length; i++)
                        acc.Obj.AppendLine("vt " + verts[i].U.ToString("0.######", IC) + " " + (1f - verts[i].W).ToString("0.######", IC));

                long ioff = ibBase + (long)sec.StartIndex * idxSize;
                for (int t = 0; t < sec.PrimitiveCount; t++)
                {
                    long p = ioff + (long)t * 3 * idxSize;
                    if (p < 0 || p + 3 * idxSize > buf.Length) { acc.Warn.Add("idxoob"); break; }
                    int a, b2, c;
                    if (idxSize == 2)
                    {
                        a = BitConverter.ToUInt16(buf, (int)p);
                        b2 = BitConverter.ToUInt16(buf, (int)(p + 2));
                        c = BitConverter.ToUInt16(buf, (int)(p + 4));
                    }
                    else
                    {
                        a = BitConverter.ToInt32(buf, (int)p);
                        b2 = BitConverter.ToInt32(buf, (int)(p + 4));
                        c = BitConverter.ToInt32(buf, (int)(p + 8));
                    }
                    if (a >= sec.VertexCount || b2 >= sec.VertexCount || c >= sec.VertexCount) continue;
                    if (a == b2 || b2 == c || a == c) continue;
                    int ia = acc.VBase + a, ib = acc.VBase + b2, ic = acc.VBase + c;
                    if (gotUv)
                        acc.Obj.AppendLine("f " + ia + "/" + ia + " " + ib + "/" + ib + " " + ic + "/" + ic);
                    else
                        acc.Obj.AppendLine("f " + ia + " " + ib + " " + ic);
                    acc.Tris++;
                }
                acc.VBase += (int)sec.VertexCount;
                acc.Sections++;
                localSec++;
            }
            return wroteObject;
        }

        static void WriteOut(Acc acc, string objPath, string header)
        {
            string dir = Path.GetDirectoryName(objPath);
            Directory.CreateDirectory(dir);
            string mtlName = Path.GetFileNameWithoutExtension(objPath) + ".mtl";

            var head = new StringBuilder();
            head.AppendLine("# " + header);
            head.AppendLine("# units: meters, Y-up, +Z = front of car");
            head.AppendLine("mtllib " + mtlName);

            File.WriteAllText(objPath, head.ToString() + acc.Obj.ToString());

            var mtl = new StringBuilder();
            foreach (string m in acc.Mats.OrderBy(x => x, StringComparer.Ordinal))
            {
                mtl.AppendLine("newmtl " + m);
                mtl.AppendLine("Kd 0.800 0.800 0.800");
                mtl.AppendLine("Ks 0.200 0.200 0.200");
                mtl.AppendLine("illum 2");
                mtl.AppendLine("d 1.0");
                mtl.AppendLine("");
            }
            File.WriteAllText(Path.Combine(dir, mtlName), mtl.ToString());
        }

        /// Export one mesh asset to its own OBJ.
        public static string ExportOne(string meshName, string objPath, int lod, bool onlyRenderable)
        {
            var acc = new Acc();
            string objName = Sanitize(meshName.Substring(meshName.LastIndexOf('/') + 1));
            if (!AppendMesh(acc, meshName, objName, lod, onlyRenderable)) return "SKIP [" + string.Join(",", acc.Warn.ToArray()) + "]";
            WriteOut(acc, objPath, "NFS Heat: " + meshName);
            return "OK sec=" + acc.Sections + " tris=" + acc.Tris + " verts=" + (acc.VBase - 1);
        }

        /// Export several mesh assets merged into one OBJ (each as its own "o" object).
        public static string ExportMerged(string[] meshNames, string[] objectNames, string objPath, int lod, bool onlyRenderable, string header)
        {
            var acc = new Acc();
            int ok = 0;
            for (int i = 0; i < meshNames.Length; i++)
            {
                string on = (objectNames != null && i < objectNames.Length && !string.IsNullOrEmpty(objectNames[i]))
                    ? objectNames[i]
                    : Sanitize(meshNames[i].Substring(meshNames[i].LastIndexOf('/') + 1));
                if (AppendMesh(acc, meshNames[i], Sanitize(on), lod, onlyRenderable)) ok++;
            }
            if (ok == 0) return "SKIP nothing [" + string.Join(",", acc.Warn.ToArray()) + "]";
            WriteOut(acc, objPath, header);
            return "OK parts=" + ok + "/" + meshNames.Length + " sec=" + acc.Sections + " tris=" + acc.Tris + " verts=" + (acc.VBase - 1) +
                   (acc.Warn.Count > 0 ? " warn=[" + string.Join(",", acc.Warn.Take(6).ToArray()) + "]" : "");
        }

        // ================= TEXTURES =================

        /// All Texture res entries whose name starts with the given prefix.
        public static string[] ListTextures(string prefix)
        {
            var l = new List<string>();
            foreach (ResAssetEntry r in Am.EnumerateRes(0, false, ""))
            {
                if (r.Type != "Texture") continue;
                if (r.Name.StartsWith(prefix, StringComparison.Ordinal)) l.Add(r.Name);
            }
            l.Sort(StringComparer.Ordinal);
            return l.ToArray();
        }

        /// Export one texture. fmt is "png" or "dds".
        public static string ExportTexture(string texName, string outPath, string fmt)
        {
            ResAssetEntry res = Am.GetResEntry(texName);
            if (res == null) return "ERR no res";
            if (res.Type != "Texture") return "ERR not a texture (" + res.Type + ")";
            Texture tex;
            try { tex = Am.GetResAs<Texture>(res, null); }
            catch (Exception ex) { return "ERR read: " + ex.GetType().Name + " " + ex.Message; }
            try
            {
                Directory.CreateDirectory(Path.GetDirectoryName(outPath));
                var exp = new TextureExporter();
                exp.Export(tex, outPath, "*." + fmt);
            }
            catch (Exception ex) { return "ERR export: " + ex.GetType().Name + " " + ex.Message; }
            if (!File.Exists(outPath)) return "ERR no file written";
            return "OK " + tex.Width + "x" + tex.Height + " " + tex.PixelFormat + " " + new FileInfo(outPath).Length + "B";
        }

        static string Sanitize(string s)
        {
            var sb = new StringBuilder();
            foreach (char c in s) sb.Append((char.IsLetterOrDigit(c) || c == '_' || c == '-') ? c : '_');
            return sb.ToString();
        }
    }
}
