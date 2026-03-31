const seed = {
  title: "雾港回声：分歧之夜",
  nodes: [
    { id: "N00_intro", label: "归乡开场", next: ["N10_archive", "N20_cafe"] },
    { id: "N10_archive", label: "旧校舍档案室", next: ["N30_confession"] },
    { id: "N20_cafe", label: "夜间咖啡馆", next: ["N30_confession"] },
    { id: "N30_confession", label: "暴雨告白", next: ["E01_truth", "E02_silence"] },
    { id: "E01_truth", label: "真相结局", next: [] },
    { id: "E02_silence", label: "沉默结局", next: [] }
  ]
};

function byId(id) { return document.getElementById(id); }

function renderNodes() {
  const host = byId("nodes");
  host.innerHTML = "";
  seed.nodes.forEach((n) => {
    const row = document.createElement("div");
    row.className = "node";
    row.textContent = `${n.id} | ${n.label} -> ${n.next.length ? n.next.join(", ") : "END"}`;
    host.appendChild(row);
  });
}

function exportJson() {
  const payload = {
    project: byId("projectTitle").value,
    pitch: byId("projectPitch").value,
    story_tree: seed.nodes
  };
  byId("output").textContent = JSON.stringify(payload, null, 2);
}

function exportMd() {
  const p = byId("projectTitle").value;
  const pitch = byId("projectPitch").value;
  const lines = [];
  lines.push(`# ${p}`);
  lines.push("");
  lines.push("## 00 项目概览");
  lines.push(pitch || "（待补）");
  lines.push("");
  lines.push("## 01 剧情树");
  seed.nodes.forEach((n) => lines.push(`- ${n.id} ${n.label} -> ${n.next.length ? n.next.join(", ") : "END"}`));
  lines.push("");
  lines.push("## 02 世界观背景");
  lines.push("- 地点：海港小镇，长期笼罩季风与雾气");
  lines.push("- 主题：记忆、承诺与失语");
  byId("output").textContent = lines.join("\n");
}

byId("btnJson").addEventListener("click", exportJson);
byId("btnMd").addEventListener("click", exportMd);
renderNodes();
exportJson();
