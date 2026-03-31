const $ = (id) => document.getElementById(id);
const seed = {
  title: '雾港回声',
  nodes: [
    { id:'intro_return_home', label:'归乡开场', to:['school_archive','cafe_evening'] },
    { id:'school_archive', label:'旧校舍档案室', to:['storm_confession'] },
    { id:'cafe_evening', label:'夜间咖啡馆', to:['storm_confession'] },
    { id:'storm_confession', label:'暴雨告白', to:['ending_truth','ending_silence'] },
    { id:'ending_truth', label:'真相结局', to:[] },
    { id:'ending_silence', label:'沉默结局', to:[] },
  ]
};
function drawRows() {
  const host = $('branchRows'); host.innerHTML='';
  seed.nodes.forEach((n) => {
    const div = document.createElement('div'); div.className='branch-row';
    div.innerHTML = `<span class='tag'>${n.id}</span><strong>${n.label}</strong><span class='muted'>-> ${n.to.join(', ') || 'END'}</span>`;
    host.appendChild(div);
  });
  $('kpiNodeCount').textContent = String(seed.nodes.length);
  $('kpiBranchCount').textContent = String(seed.nodes.filter(n => n.to.length > 1).length);
}
function exportJSON() {
  const payload = {
    title: $('titleInput').value || seed.title,
    theme: $('themeInput').value,
    core_conflict: $('conflictInput').value,
    node_flow: seed.nodes,
    role_background: $('roleInput').value.split('\n').filter(Boolean),
    scene_background: $('sceneInput').value.split('\n').filter(Boolean),
  };
  $('jsonOut').textContent = JSON.stringify(payload, null, 2);
  $('kpiUpdated').textContent = new Date().toLocaleString();
}
function exportMarkdown() {
  const lines = [];
  lines.push('# ' + ($('titleInput').value || seed.title));
  lines.push('');
  lines.push('## 主冲突');
  lines.push($('conflictInput').value || '（待补）');
  lines.push('');
  lines.push('## 节点流');
  seed.nodes.forEach((n) => lines.push(`- ${n.id} ${n.label} -> ${n.to.join(', ') || 'END'}`));
  $('mdOut').textContent = lines.join('\n');
}
$('btnJson').addEventListener('click', exportJSON);
$('btnMd').addEventListener('click', exportMarkdown);
drawRows(); exportJSON();
