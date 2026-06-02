/**
 * TheDailyMe — Web 客户端交互逻辑
 * 纯原生 JS，无框架依赖
 */

// ── 状态 ──────────────────────────────────────────────────
const STATE = {
  activePanel: 'today',
  generating: false,
  pollTimer: null,
  config: null,
  archives: [],
  todayExists: false,
};

// ── DOM 引用 ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const SPIRAL_PATH = 'M58.00,50.00L57.84,51.67L57.36,53.28L56.58,54.78L55.51,56.12L54.19,57.25L52.64,58.12L50.91,58.68L49.07,58.89L47.16,58.74L45.27,58.19L43.47,57.25L41.84,55.93L40.47,54.24L39.44,52.25L38.81,50.00L38.65,47.59L39.00,45.10L39.89,42.66L41.33,40.37L43.27,38.35L45.69,36.73L48.49,35.61L51.57,35.09L54.80,35.23L58.04,36.08L61.13,37.64L63.91,39.89L66.23,42.78L67.93,46.19L68.90,50.00L69.04,54.05L68.31,58.15L66.67,62.11L64.16,65.73L60.86,68.81L56.88,71.18L52.38,72.68L47.56,73.21L42.63,72.68L37.83,71.09L33.38,68.46L29.53,64.88L26.47,60.48L24.38,55.45L23.39,50.00L23.59,44.39L25.00,38.87L27.58,33.71L31.24,29.16L35.83,25.46L41.16,22.79L46.98,21.30L53.04,21.08L59.04,22.17L64.71,24.51L69.78,28.03L74.00,32.56L77.17,37.90L79.13,43.81L79.80,50.00L79.13,56.19L77.17,62.10L74.00,67.44L69.78,71.97L64.71,75.49L59.04,77.83L53.04,78.92L46.98,78.70L41.16,77.21L35.83,74.54L31.24,70.84L27.58,66.29L25.00,61.13L23.59,55.61L23.39,50.00L24.38,44.55L26.47,39.52L29.53,35.13L33.38,31.54L37.82,28.91L42.63,27.32L47.56,26.79L52.38,27.32L56.88,28.82L60.86,31.19L64.16,34.27L66.67,37.89L68.31,41.85L69.04,45.95L68.90,50.00L67.93,53.81L66.23,57.22L63.91,60.11L61.13,62.36L58.04,63.92L54.80,64.77L51.57,64.91L48.49,64.39L45.69,63.27L43.28,61.65L41.33,59.63L39.89,57.34L39.00,54.90L38.65,52.41L38.81,50.00L39.44,47.75L40.47,45.76L41.84,44.07L43.47,42.75L45.27,41.81L47.16,41.26L49.07,41.11L50.91,41.32L52.64,41.88L54.19,42.75L55.51,43.88L56.58,45.22L57.36,46.72L57.84,48.33L58.00,50.00';

const LOADER_SVG = '<svg class="spiral-loader" viewBox="0 0 100 100" fill="none"><path class="spiral-path" d="' + SPIRAL_PATH + '" stroke="currentColor" stroke-width="0.8" opacity="0.12" stroke-linecap="round" stroke-linejoin="round"/><path class="spiral-trail" d="' + SPIRAL_PATH + '" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="400 1400"/></svg>';

const panels = {
  today: $('#panel-today'),
  archive: $('#panel-archive'),
  settings: $('#panel-settings'),
};
const navLinks = $$('.sidebar nav a');
const statusDot = $('#statusDot');
const statusText = $('#statusText');

// ── 工具函数 ──────────────────────────────────────────────

function showToast(msg, type = 'success') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2500);
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日`;
}

// ── 导航 ──────────────────────────────────────────────────

function switchPanel(name) {
  STATE.activePanel = name;
  Object.values(panels).forEach(p => p.classList.remove('active'));
  panels[name].classList.add('active');
  navLinks.forEach(a => {
    a.classList.toggle('active', a.dataset.panel === name);
  });

  if (name === 'today') refreshToday();
  if (name === 'archive') refreshArchive();
  if (name === 'settings') refreshSettings();
}

navLinks.forEach(a => {
  a.addEventListener('click', (e) => {
    e.preventDefault();
    switchPanel(a.dataset.panel);
  });
});

// ── 状态指示器 ────────────────────────────────────────────

function updateStatus(generating) {
  STATE.generating = generating;
  statusDot.className = 'dot ' + (generating ? 'running' : 'ok');
  statusText.textContent = generating ? '生成中...' : '就绪';
}

// ── Today Panel ───────────────────────────────────────────

async function refreshToday() {
  let status;
  try {
    status = await fetch('/api/status').then(r => r.json());
  } catch (e) {
    panels.today.innerHTML = '<div class="today-empty"><p>无法连接到服务</p></div>';
    return;
  }

  STATE.todayExists = status.today_exists;
  updateStatus(status.generating);

  if (status.generating || status.today_exists === false) {
    renderTodayEmpty(status);
    if (status.generating) startPolling();
  } else {
    renderTodayReport(status.today);
  }
}

function renderTodayEmpty(status) {
  let html = '<div class="today-empty">';
  if (status.generating) {
    html += `
      <div class="progress-card">
        ${LOADER_SVG}
        <div class="stage">${status.gen_stage === 'fetching' ? '正在采集数据' : status.gen_stage === 'rendering' ? '正在排版' : '正在准备...'}</div>
        <div class="detail" id="genDetail">${status.gen_detail || ''}</div>
      </div>`;
  } else if (status.gen_error) {
    html += `
      <h2>生成失败</h2>
      <p>${status.gen_error}</p>
      <button class="btn btn-primary" onclick="startGenerate()"><i class="icon icon-refresh"></i> 重试</button>`;
  } else {
    html += `
      <h2><i class="icon icon-newspaper"></i> 今日日报尚未生成</h2>
      <p>点击按钮，为你从 ${STATE.config ? '配置的数据源' : '互联网'} 采集最新内容</p>
      <button class="btn btn-primary" id="btnGenerate" onclick="startGenerate()"><i class="icon icon-zap"></i> 生成今日日报</button>`;
  }
  html += '</div>';
  panels.today.innerHTML = html;
}

function renderTodayReport(today) {
  panels.today.innerHTML = `
    <div class="today-report">
      <div class="toolbar">
        <h2><i class="icon icon-newspaper"></i> ${formatDate(today)} 日报</h2>
        <button class="btn btn-sm btn-primary" onclick="startGenerate()"><i class="icon icon-refresh"></i> 重新生成</button>
      </div>
      <iframe src="/report/${today}" scrolling="no" onload="this.style.height=this.contentWindow.document.body.scrollHeight+'px'"></iframe>
    </div>`;
}

// ── 生成流程 ──────────────────────────────────────────────

async function startGenerate() {
  const btn = $('#btnGenerate');
  if (btn) btn.disabled = true;
  updateStatus(true);

  panels.today.innerHTML = `
    <div class="today-empty">
      <div class="progress-card">
        ${LOADER_SVG}
        <div class="stage">正在启动...</div>
        <div class="detail"></div>
      </div>
    </div>`;

  try {
    const resp = await fetch('/api/generate', { method: 'POST' });
    const data = await resp.json();
    if (!data.ok) {
      showToast(data.error || '生成失败', 'error');
      refreshToday();
      return;
    }
    startPolling();
  } catch (e) {
    showToast('请求失败: ' + e.message, 'error');
    refreshToday();
  }
}

function startPolling() {
  if (STATE.pollTimer) clearInterval(STATE.pollTimer);
  STATE.pollTimer = setInterval(async () => {
    try {
      const status = await fetch('/api/status').then(r => r.json());
      const stageEl = $('.progress-card .stage');
      const detailEl = $('.progress-card .detail');
      if (stageEl) {
        const stageMap = { init: '正在初始化...', fetching: '正在采集数据', processing: '正在分析处理...', ai: 'AI 正在分析...', rendering: '正在排版...', done: '完成', error: '出错' };
        stageEl.textContent = stageMap[status.gen_stage] || status.gen_stage;
      }
      if (detailEl) detailEl.textContent = status.gen_detail || '';

      if (!status.generating) {
        clearInterval(STATE.pollTimer);
        STATE.pollTimer = null;
        updateStatus(false);

        if (status.gen_error) {
          refreshToday();
          showToast(status.gen_error, 'error');
        } else {
          setTimeout(() => refreshToday(), 500);
        }
      }
    } catch (e) { /* ignore */ }
  }, 800);
}

// ── Archive Panel ─────────────────────────────────────────

async function refreshArchive() {
  try {
    STATE.archives = await fetch('/api/archives').then(r => r.json());
  } catch (e) {
    STATE.archives = [];
  }

  const listEl = $('#archiveList');
  const previewEl = $('#archivePreview');

  if (!STATE.archives.length) {
    listEl.innerHTML = '<h3>历史日报</h3><p style="color:var(--muted);font-size:13px;">暂无存档</p>';
    previewEl.innerHTML = '<div class="archive-empty">还没有生成过日报</div>';
    return;
  }

  listEl.innerHTML = '<h3>历史日报</h3>' + STATE.archives.map(a => `
    <div class="archive-item" data-date="${a.date}" onclick="previewArchive('${a.date}', this)">
      <span class="date">${a.date}</span>
      <span class="del" title="删除" onclick="deleteArchive(event, '${a.date}')">×</span>
    </div>
  `).join('');

  previewEl.innerHTML = '<div class="archive-empty">选择日期查看历史日报</div>';
}

function previewArchive(date, el) {
  // 高亮
  $$('.archive-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');

  $('#archivePreview').innerHTML = `
    <iframe src="/report/${date}" scrolling="no" onload="this.style.height=this.contentWindow.document.body.scrollHeight+'px'"></iframe>`;
}

async function deleteArchive(e, date) {
  e.stopPropagation();
  if (!confirm(`确定删除 ${date} 的日报吗？`)) return;
  try {
    await fetch(`/api/report/${date}`, { method: 'DELETE' });
    showToast(`已删除 ${date} 日报`);
    refreshArchive();
  } catch (err) {
    showToast('删除失败', 'error');
  }
}

// ── Settings Panel ────────────────────────────────────────

async function refreshSettings() {
  if (!STATE.config) {
    try {
      STATE.config = await fetch('/api/config').then(r => r.json());
    } catch (e) {
      $('#settingsContent').innerHTML = '<p>无法加载配置</p>';
      return;
    }
  }

  renderSettingsForm(STATE.config);
}

function renderSettingsForm(cfg) {
  const user = cfg.user || {};
  const cats = cfg.categories || {};
  const srcs = cfg.sources || {};
  const fetchCfg = cfg.fetch || {};
  const topicSel = cfg.topic_selection || {};

  const cityOptions = [
    'Beijing','Shanghai','Guangzhou','Shenzhen','Chengdu','Hangzhou',
    'Wuhan','Nanjing','Chongqing','Tianjin','Xian','Suzhou','Changsha',
    'Zhengzhou','Qingdao','Dalian','Xiamen','Kunming','Harbin','Shenyang',
    'Tokyo','Seoul','Singapore','Bangkok','Hong Kong','Taipei','Dubai',
    'London','Paris','Berlin','Moscow','Rome','Madrid','Amsterdam',
    'New York','Los Angeles','Chicago','San Francisco','Toronto',
    'Sydney','Melbourne',
  ];

  const loadHierarchyAndRender = function(hierarchy) {
    TOPIC_HIERARCHY = hierarchy;
    $('#settingsContent').innerHTML = `
    <h2><i class="icon icon-settings"></i> 设置</h2>

    <div class="settings-section">
      <h3><i class="icon icon-user"></i> 个人信息</h3>
      <div class="form-group">
        <label>你的名字</label>
        <input type="text" id="cfgName" value="${esc(user.name || '')}" placeholder="同学">
      </div>
      <div class="form-group">
        <label>所在城市（用于天气）</label>
        <select id="cfgCity">
          ${cityOptions.map(c => `<option value="${c}" ${user.city===c?'selected':''}>${c}</option>`).join('')}
        </select>
      </div>
    </div>

    <div class="settings-section">
      <h3><i class="icon icon-palette"></i> 排版风格</h3>
      <div class="form-group">
        <label>选择日报的视觉风格（下次生成生效）</label>
        <select id="cfgLayout">
          <option value="broadsheet" ${(cfg.layout||'broadsheet')==='broadsheet'?'selected':''}>报纸头版 — 经典 broadsheet，衬线体，多栏</option>
          <option value="swiss" ${cfg.layout==='swiss'?'selected':''}>瑞士国际主义 — 网格系统，无衬线，大面积留白</option>
          <option value="cyberpunk" ${cfg.layout==='cyberpunk'?'selected':''}>赛博朋克终端 — 暗底霓虹，等宽字体，CRT 扫描线</option>
          <option value="magazine" ${cfg.layout==='magazine'?'selected':''}>杂志排版 — Garamond 衬线，暖色，装饰点缀</option>
        </select>
      </div>
    </div>

    ${renderTopicSelector(topicSel, hierarchy)}

    ${renderWeightsSection(cats, topicSel, hierarchy)}

    <div class="settings-section">
      <h3>数据源开关</h3>
      ${Object.entries(srcs).map(([cat, catSrcs]) => `
        <p style="font-weight:600;font-size:13px;margin:12px 0 6px;">${catLabel(cat)}</p>
        ${Object.entries(catSrcs).map(([key, val]) => `
          <div class="toggle-row">
            <span class="toggle-label">${srcLabel(key)}</span>
            <label class="toggle-switch">
              <input type="checkbox" id="cfgSrc_${cat}_${key}" ${val!==false?'checked':''}>
              <span class="slider"></span>
            </label>
          </div>
        `).join('')}
      `).join('')}
    </div>

    <div class="settings-section">
      <h3>采集参数</h3>
      <div class="form-group">
        <label>每个源最多取几条</label>
        <input type="range" min="3" max="20" value="${fetchCfg.articles_per_source||5}"
               id="cfgPerSource" oninput="$('#perSourceVal').textContent=this.value">
        <span id="perSourceVal" style="font-weight:600;">${fetchCfg.articles_per_source||5}</span> 条
      </div>
      <div class="form-group">
        <label>请求超时（秒）</label>
        <input type="text" id="cfgTimeout" value="${fetchCfg.request_timeout||10}" style="width:80px">
      </div>
    </div>

    <div class="settings-section">
      <h3><i class="icon icon-bot"></i> AI 增强</h3>
      <div class="toggle-row">
        <span class="toggle-label">启用 AI 头条筛选与总结</span>
        <label class="toggle-switch">
          <input type="checkbox" id="cfgAIEnabled" ${(cfg.ai||{}).enabled!==false?'checked':''}>
          <span class="slider"></span>
        </label>
      </div>
      <div class="form-group" style="margin-top:12px;">
        <label>API 地址（支持 OpenAI 兼容接口）</label>
        <input type="text" id="cfgAIBaseUrl" value="${esc((cfg.ai||{}).base_url||'https://api.openai.com/v1')}" placeholder="https://api.openai.com/v1">
      </div>
      <div class="form-group">
        <label>API Key</label>
        <input type="password" id="cfgAIKey" value="${esc((cfg.ai||{}).api_key||'')}" placeholder="sk-...">
      </div>
      <div class="form-group">
        <label>模型名称</label>
        <input type="text" id="cfgAIModel" value="${esc((cfg.ai||{}).model||'gpt-4o-mini')}" placeholder="gpt-4o-mini">
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:4px;">
        AI 启用后，大模型会自动从所有新闻中选出 3-5 条最重要的头条，
        重写标题、生成二级详情页深度解读内容，并提供今日必读简报。
        未配置 API Key 时自动回退到传统模式。
      </p>
    </div>

    <div class="settings-actions">
      <button class="btn btn-primary" onclick="saveSettings()"><i class="icon icon-save"></i> 保存设置</button>
    </div>
  `;
  };

  if (Object.keys(TOPIC_HIERARCHY).length === 0) {
    fetch('/api/topic-hierarchy')
      .then(r => r.json())
      .then(h => { TOPIC_HIERARCHY = h; loadHierarchyAndRender(h); })
      .catch(() => {
        TOPIC_HIERARCHY = FALLBACK_HIERARCHY;
        loadHierarchyAndRender(FALLBACK_HIERARCHY);
      });
  } else {
    loadHierarchyAndRender(TOPIC_HIERARCHY);
  }
}

function catLabel(c) {
  return {tech:'科技', climate:'气候', gaming:'游戏', sports:'体育', movies:'影视', music:'音乐'}[c] || c;
}
function srcLabel(k) {
  return {
    github_trending:'GitHub Trending', hackernews:'Hacker News', v2ex:'V2EX',
    open_meteo:'Open-Meteo 天气', weather_rss:'天气 RSS', carbon_brief:'Carbon Brief',
    steam_rss:'Steam 新闻', reddit_gaming:'Reddit r/gaming', youmin_rss:'游民星空',
    espn_rss:'ESPN', hupu:'虎扑', reddit_sports:'Reddit r/sports',
    douban_rss:'豆瓣电影', reddit_movies:'Reddit r/movies', rottentomatoes_rss:'烂番茄',
    reddit_music:'Reddit r/music', pitchfork_rss:'Pitchfork', billboard_rss:'Billboard',
  }[k] || k;
}
function esc(s) { return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }

var TOPIC_HIERARCHY = {};
var FALLBACK_HIERARCHY = {
  tech: { label: '科技', sub_topics: [
    {key:'ai',label:'AI'},{key:'opensource',label:'开源'},{key:'security',label:'安全'},
    {key:'programming',label:'编程'},{key:'internet',label:'互联网'}
  ]},
  climate: { label: '气候', sub_topics: [
    {key:'extreme_weather',label:'极端天气'},{key:'policy',label:'气候政策'},
    {key:'energy',label:'能源转型'},{key:'ecology',label:'生态'}
  ]},
  gaming: { label: '游戏', sub_topics: [
    {key:'pc',label:'PC游戏'},{key:'console',label:'主机'},{key:'mobile',label:'手游'},
    {key:'esports',label:'电竞'},{key:'industry',label:'行业'}
  ]},
  sports: { label: '体育', sub_topics: [
    {key:'basketball',label:'篮球'},{key:'football',label:'足球'},
    {key:'tennis',label:'网球'},{key:'combat',label:'格斗'}
  ]},
  movies: { label: '影视', sub_topics: [
    {key:'new_release',label:'新片'},{key:'box_office',label:'票房'},
    {key:'review',label:'评价'},{key:'streaming',label:'流媒体'}
  ]},
  music: { label: '音乐', sub_topics: [
    {key:'charts',label:'榜单'},{key:'pop',label:'流行'},
    {key:'electronic',label:'电子'},{key:'indie',label:'独立/摇滚'}
  ]},
};

function getTopicSel() {
  return (STATE.config || {}).topic_selection || {};
}

function renderTopicSelector(topicSel, hierarchy) {
  var html = '<h3><i class="icon icon-tag"></i> 主题选择</h3>';
  html += '<p style="font-size:12px;color:var(--muted);margin:-8px 0 12px;">勾选你想看的大主题，展开后可进一步选择子主题。未勾选的大主题不会出现在日报中。</p><div class="topic-list">';

  ['tech','climate','gaming','sports','movies','music'].forEach(function(ck) {
    var cat = hierarchy[ck] || {};
    var sel = topicSel[ck] || {};
    var selected = sel.selected !== false;
    var subSel = sel.sub_topics || [];
    var hasFilter = subSel.length > 0;
    var subs = cat.sub_topics || [];

    html += '<div class="topic-row">';
    html += '<label class="topic-check">';
    html += '<input type="checkbox" id="topicMain_' + ck + '" ' + (selected ? 'checked' : '') + ' onchange="onMainTopicChange(\'' + ck + '\')">';
    html += '<span>' + (cat.label || ck) + '</span></label>';

    if (subs.length) {
      var badgeText = selected && hasFilter ? subSel.length + '/' + subs.length : selected ? '全部' : '';
      var badgeStyle = badgeText ? '' : ' style="display:none"';
      html += '<button type="button" class="topic-expand-btn" id="topicExpand_' + ck + '" onclick="toggleSubTopicPanel(\'' + ck + '\')" ' + (!selected ? 'disabled' : '') + '>▸</button>';
      html += '<span class="topic-filter-badge' + (!hasFilter && selected ? ' all' : '') + '" id="topicBadge_' + ck + '"' + badgeStyle + '>' + badgeText + '</span>';
    }
    html += '</div>';

    if (subs.length) {
      var showPanel = selected && hasFilter;
      html += '<div class="topic-sub-panel" id="topicSubPanel_' + ck + '"' + (!showPanel ? ' style="display:none"' : '') + '>';
      subs.forEach(function(st) {
        var subChk = !hasFilter || subSel.indexOf(st.key) >= 0;
        html += '<label class="topic-sub-check"><input type="checkbox" id="topicSub_' + ck + '_' + st.key + '" ' + (subChk ? 'checked' : '') + ' onchange="onSubTopicChange(\'' + ck + '\')" ' + (!selected ? 'disabled' : '') + '><span>' + st.label + '</span></label>';
      });
      html += '<div class="topic-sub-actions"><button type="button" class="btn btn-sm" onclick="selectAllSubs(\'' + ck + '\')">全选</button><button type="button" class="btn btn-sm" onclick="clearSubs(\'' + ck + '\')">清除</button></div>';
      html += '</div>';
    }
  });

  html += '</div>';
  return '<div class="settings-section">' + html + '</div>';
}

function renderWeightsSection(cats, topicSel, hierarchy) {
  var allCats = ['tech','climate','gaming','sports','movies','music'];
  var visible = allCats.filter(function(ck) { return (topicSel[ck] || {}).selected !== false; });

  var html = '<h3>类别权重（仅显示已选主题）</h3>';
  if (!visible.length) {
    html += '<p style="color:var(--muted);font-size:13px;">请在"主题选择"中至少勾选一个大主题</p>';
  } else {
    visible.forEach(function(ck) {
      var sel = topicSel[ck] || {};
      var subSel = sel.sub_topics || [];
      var cat = hierarchy[ck] || {};
      var w = Math.round((cats[ck] || 0.33) * 100);
      html += '<div class="form-group weight-group"><label>' + (cat.label || ck) + ' — <span id="' + ck + 'Val">' + w + '%</span></label>';
      html += '<div class="range-row"><input type="range" min="0" max="100" value="' + w + '" id="cfgCat_' + ck + '" oninput="onWeightChange()"></div>';

      if (subSel.length) {
        (cat.sub_topics || []).filter(function(st) { return subSel.indexOf(st.key) >= 0; }).forEach(function(st) {
          var sid = ck + '__' + st.key;
          var sw = Math.round(100 / subSel.length);
          html += '<div class="form-group weight-sub"><label>└ ' + st.label + ' — <span id="' + sid + 'Val">' + sw + '%</span></label>';
          html += '<div class="range-row"><input type="range" min="0" max="100" value="' + sw + '" id="cfgSub_' + sid + '" oninput="onSubWeightChange()"></div></div>';
        });
      }
      html += '</div>';
    });
  }
  return '<div class="settings-section" id="weightsSection">' + html + '</div>';
}

function toggleSubTopicPanel(ck) {
  var btn = $('#topicExpand_' + ck);
  var panel = $('#topicSubPanel_' + ck);
  if (!btn || !panel) return;
  if (panel.style.display === 'none') { panel.style.display = ''; btn.textContent = '▾'; }
  else { panel.style.display = 'none'; btn.textContent = '▸'; }
}

function onMainTopicChange(ck) {
  var checked = $('#topicMain_' + ck).checked;
  var panel = $('#topicSubPanel_' + ck);
  var btn = $('#topicExpand_' + ck);
  if (panel) panel.style.display = 'none';
  if (btn) { btn.textContent = '▸'; btn.disabled = !checked; }
  var cbs = document.querySelectorAll('[id^="topicSub_' + ck + '_"]');
  cbs.forEach(function(cb) { cb.disabled = !checked; });
  refreshWeights();
  updateBadge(ck);
}

function onSubTopicChange(ck) {
  refreshWeights();
  updateBadge(ck);
}

function selectAllSubs(ck) {
  var main = $('#topicMain_' + ck);
  if (!main || !main.checked) return;
  document.querySelectorAll('[id^="topicSub_' + ck + '_"]').forEach(function(cb) { cb.checked = true; });
  refreshWeights();
  updateBadge(ck);
  var p = $('#topicSubPanel_' + ck); if (p) p.style.display = '';
  var b = $('#topicExpand_' + ck); if (b) b.textContent = '▾';
}

function clearSubs(ck) {
  document.querySelectorAll('[id^="topicSub_' + ck + '_"]').forEach(function(cb) { cb.checked = false; });
  refreshWeights();
  updateBadge(ck);
}

function updateBadge(ck) {
  var main = $('#topicMain_' + ck);
  var badge = $('#topicBadge_' + ck);
  if (!main || !badge) return;
  if (!main.checked) { badge.style.display = 'none'; return; }
  var cbs = document.querySelectorAll('[id^="topicSub_' + ck + '_"]');
  var anyOff = false, anyOn = false;
  cbs.forEach(function(cb) { if (cb.checked) anyOn = true; else anyOff = true; });
  badge.style.display = '';
  if (anyOn && anyOff) { var n = 0; cbs.forEach(function(cb) { if (cb.checked) n++; }); badge.textContent = n + '/' + cbs.length; badge.className = 'topic-filter-badge'; }
  else { badge.textContent = '全部'; badge.className = 'topic-filter-badge all'; }
}

function refreshWeights() {
  var sel = readTopicSelection();
  var cfg = STATE.config || {};
  var cats = cfg.categories || {};
  var hier = Object.keys(TOPIC_HIERARCHY).length > 0 ? TOPIC_HIERARCHY : FALLBACK_HIERARCHY;
  var ws = $('#weightsSection');
  if (ws) { var div = document.createElement('div'); div.innerHTML = renderWeightsSection(cats, sel, hier); ws.replaceWith(div.firstChild); }
}

function readTopicSelection() {
  var r = {};
  ['tech','climate','gaming','sports','movies','music'].forEach(function(ck) {
    var m = $('#topicMain_' + ck);
    if (!m) { r[ck] = {selected: true, sub_topics: []}; return; }
    var sel = m.checked, subs = [];
    if (sel) {
      var anyOff = false;
      document.querySelectorAll('[id^="topicSub_' + ck + '_"]').forEach(function(cb) {
        if (!cb.checked) anyOff = true;
        else { var parts = cb.id.split('_'); subs.push(parts.slice(2).join('_')); }
      });
      if (!anyOff) subs = [];
    }
    r[ck] = {selected: sel, sub_topics: subs};
  });
  return r;
}

function onWeightChange() {
  ['tech','climate','gaming','sports','movies','music'].forEach(function(c) {
    var el = $('#cfgCat_' + c);
    if (el) { var v = parseInt(el.value) || 0; var ve = $('#' + c + 'Val'); if (ve) ve.textContent = v + '%'; }
  });
}

function onSubWeightChange() {
  document.querySelectorAll('[id^="cfgSub_"]').forEach(function(el) {
    var id = el.id.replace('cfgSub_', '');
    var ve = $('#' + id + 'Val');
    if (ve) ve.textContent = (parseInt(el.value) || 0) + '%';
  });
}

async function saveSettings() {
  const name = $('#cfgName').value.trim() || '同学';
  const city = $('#cfgCity').value;

  const cats = {};
  ['tech','climate','gaming','sports','movies','music'].forEach(c => {
    cats[c] = parseInt($('#cfgCat_'+c).value) / 100;
  });

  const srcs = {};
  ['tech','climate','gaming','sports','movies','music'].forEach(cat => {
    srcs[cat] = {};
    const keys = cat === 'tech' ? ['github_trending','hackernews','v2ex']
      : cat === 'climate' ? ['open_meteo','weather_rss','carbon_brief']
      : cat === 'gaming' ? ['steam_rss','reddit_gaming','youmin_rss']
      : cat === 'sports' ? ['espn_rss','hupu','reddit_sports']
      : cat === 'movies' ? ['douban_rss','reddit_movies','rottentomatoes_rss']
      : ['reddit_music','pitchfork_rss','billboard_rss'];
    keys.forEach(k => {
      srcs[cat][k] = $('#cfgSrc_'+cat+'_'+k)?.checked !== false;
    });
  });

  const layout = $('#cfgLayout').value || 'broadsheet';

  const aiConfig = {
    enabled: $('#cfgAIEnabled')?.checked !== false,
    api_key: $('#cfgAIKey')?.value || '',
    base_url: $('#cfgAIBaseUrl')?.value || 'https://api.openai.com/v1',
    model: $('#cfgAIModel')?.value || 'gpt-4o-mini',
    max_input_articles: 60,
  };

  const config = {
    layout,
    user: { name, city, language: STATE.config?.user?.language || 'zh' },
    categories: cats,
    sources: srcs,
    topic_selection: readTopicSelection(),
    ai: aiConfig,
    fetch: {
      articles_per_source: parseInt($('#cfgPerSource').value) || 5,
      headline_pool_size: 3,
      request_timeout: parseInt($('#cfgTimeout').value) || 10,
    },
  };

  try {
    const resp = await fetch('/api/config', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(config),
    });
    const data = await resp.json();
    if (data.ok) {
      STATE.config = config;
      showToast('设置已保存');
    } else {
      showToast(data.error || '保存失败', 'error');
    }
  } catch (e) {
    showToast('保存失败: ' + e.message, 'error');
  }
}

// ── 初始化 ─────────────────────────────────────────────────

async function init() {
  try {
    STATE.config = await fetch('/api/config').then(r => r.json());
  } catch (e) { /* config 可选，后续刷新会重试 */ }
  refreshToday();
}

init();
