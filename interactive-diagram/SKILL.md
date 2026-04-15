---
name: interactive-diagram
description: "Generate interactive diagrams for mdBook projects using pure HTML + CSS + vanilla JS (zero dependencies). Supports 8 diagram types: step-by-step flow, state machine, before/after comparison, calculator/slider, tree explorer, sequence diagram, timeline, and interactive simulator. Auto-detects mdBook project, scans for ID conflicts, manages CSS, and validates quote safety. Use when user mentions: interactive diagram, 交互式图表, 交互图, flow diagram, state machine, sequence diagram, timeline, 流程图, 状态机, 时间线, 序列图, 对比图, 模拟器, mdbook diagram, mdbook interactive."
---

# mdBook Interactive Diagram Skill

为任意 mdBook 项目生成交互式图表。纯 HTML + CSS + vanilla JS，零依赖。

## 使用方式

```
/interactive-diagram
```

调用后请描述：
1. 要展示什么内容
2. 数据结构（几个节点/阶段/状态）
3. （可选）想用哪种图表类型

我会自动完成：类型选择 → 项目探测 → ID 去重 → 代码生成 → 安全验证。

---

## 第一步：项目探测（每次生成前自动执行）

```bash
# 1. 定位 mdBook 根目录（找 book.toml）
ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
BOOK_TOML=$(find "$ROOT" -name "book.toml" -maxdepth 3 | head -1)
BOOK_DIR=$(dirname "$BOOK_TOML")

# 2. 找到 custom.css 路径
CUSTOM_CSS="$BOOK_DIR/custom.css"   # 默认位置
# 如果不在根目录，检查 theme/ 下
[ ! -f "$CUSTOM_CSS" ] && CUSTOM_CSS="$BOOK_DIR/theme/custom.css"

# 3. 扫描已有的图表 ID 和函数名（避免冲突）
grep -rn 'id="rc-\|id="[a-z]*-flow\|id="[a-z]*-sm\|id="[a-z]*-seq' "$BOOK_DIR/src/" --include='*.md'
grep -rn 'window\.\(show\|reset\|switch\|play\|toggle\|update\|run\|expand\|collapse\)' "$BOOK_DIR/src/" --include='*.md'

# 4. 检查哪些图表类型的 CSS 已存在
for prefix in rc-flow rc-sm rc-cmp rc-calc rc-tree rc-seq rc-tl rc-sim; do
  grep -q "\.$prefix " "$CUSTOM_CSS" 2>/dev/null && echo "✅ $prefix CSS exists" || echo "❌ $prefix CSS missing"
done
```

---

## 第二步：图表类型决策矩阵

| 内容模式 | 推荐图表类型 | CSS 前缀 |
|----------|-------------|---------|
| 线性流程、管道、N 步骤依次执行 | **① 分步流程图** | `.rc-flow` |
| 多状态互相跳转、有条件分支 | **② 状态机图** | `.rc-sm` |
| 新旧对比、有/无某功能对比 | **③ 前后对比图** | `.rc-cmp` |
| 数值参数可调整、实时看结果 | **④ 计算器/滑块** | `.rc-calc` |
| 层级结构、树形展开 | **⑤ 树形展开图** | `.rc-tree` |
| 多角色按时间线交互 | **⑥ 序列图** | `.rc-seq` |
| 时间线、甘特图、阶段段落 | **⑦ 时间线/甘特图** | `.rc-tl` |
| 可输入、有状态、模拟运行 | **⑧ 交互式模拟器** | `.rc-sim` |

**选型示例**：
- "CI/CD 管道 5 个阶段" → ① 分步流程图
- "HTTP 请求状态 pending/fulfilled/rejected" → ② 状态机
- "重构前后代码对比" → ③ 前后对比
- "缓存命中率 vs 容量的关系" → ④ 计算器/滑块
- "文件系统目录结构" → ⑤ 树形展开
- "客户端-服务器-数据库三方交互" → ⑥ 序列图
- "项目从 v1.0 到 v3.0 的里程碑" → ⑦ 时间线
- "模拟 SQL 查询执行过程" → ⑧ 交互式模拟器

---

## ⚠️ 安全规则（每次生成必须遵守）

### 规则 1：引号安全
```
❌ html:"...包含"引号"的内容..."     → JS 静默崩溃
❌ html:"...包含\"转义引号\"..."      → mdBook 中不可靠
✅ html:'...包含"引号"的内容...'     → 安全
✅ html:"...纯文本无引号..."          → 安全
```
**原理**：mdBook 将 `<script>` 直接嵌入 HTML，JS 字符串内的 ASCII `"` (U+0022) 会截断外层双引号，IIFE 静默失败，所有 `window.xxx` 函数永不注册。用户点击无反应、无报错。

### 规则 2：唯一 ID + 唯一函数名
- 容器 `id` 必须全书唯一（先扫描再命名）
- `window.showXxxStage` 函数名后缀必须唯一
- 命名模式：`{概念缩写}-{类型}`，如 `auth-flow`、`perm-sm`、`cache-calc`

### 规则 3：IIFE 包裹
```javascript
(function(){
  // 所有变量和逻辑
  window.showXxxStage = function(n) { /* ... */ };
})();
```

### 规则 4：CSS 管理
- 生成前检查 `custom.css` 中是否已有该类型的 CSS
- 如果缺失，将完整的 CSS 块（含 light + dark 主题）追加到 `custom.css`
- dark 主题选择器：`.navy .rc-xxx, .coal .rc-xxx`（mdBook 内置主题类名）

### 规则 5：生成后验证
```bash
# 1. 引号安全检查
python3 -c "
import sys
content = open(sys.argv[1], encoding='utf-8').read()
for i, line in enumerate(content.split('\n'), 1):
    s = line.strip()
    if 'html:\"' in s and s.count('\"') > 2:
        print(f'⚠️  Line {i}: quote nesting risk ({s.count(chr(34))} quotes)')
        print(f'   {s[:120]}')
print('✅ Quote check done')
" TARGET_FILE

# 2. 函数名唯一性
grep -rn 'window\.\(show\|reset\)' BOOK_DIR/src/ --include='*.md' | sort

# 3. mdbook build（如果可用）
cd BOOK_DIR && mdbook build 2>&1 | tail -5
```

---

## 颜色系统

### 默认颜色（可在 CSS 中自定义）

所有图表共享同一套颜色变量。如果项目已有不同的强调色，只需在 CSS 中全局替换：

| 语义 | Light 默认值 | Dark 默认值 | 用途 |
|------|-------------|------------|------|
| `ACCENT` | `#d97757` | `#d97757` | 高亮边框、活跃状态、播放按钮 |
| `ACCENT_DEEP` | `#c56a4a` | `#c56a4a` | 按钮 hover、按下状态 |
| `BORDER` | `#d0d7de` | `#30414e` | 所有边框、分隔线 |
| `BG_HEADER` | `#f0f4f8` | `#1e2a3a` | 控制栏、表头 |
| `BG_CARD` | `#f8f9fa` | `#1e2a3a` | 卡片、节点默认背景 |
| `BG_HOVER` | `#e8ecf1` | `#2a3a4a` | 悬停状态 |
| `TEXT_PRIMARY` | `#1a1a2e` | `#e0e0e0` | 标题、强调文字 |
| `TEXT_BODY` | `#2c3e50` | `#c9d1d9` | 正文 |
| `TEXT_MUTED` | `#87867f` | `#6a737d` | 辅助说明文字 |
| `SUCCESS` | `#22c55e` | `#22c55e` | 已完成状态 |
| `CODE_PINK` | `#d63384` | `#f0a8c0` | 代码标签文字 |

**自定义方式**：在 custom.css 顶部查找/替换 `#d97757` 为你的品牌色即可。

---

## 类型 ① 分步流程图

适用于：线性管道、N 步依次执行。

### HTML 模板

将 `{{ID}}` 替换为唯一 ID（如 `deploy-flow`），`{{Name}}` 替换为 PascalCase 名（如 `Deploy`）。

```html
<div class="rc-flow" id="{{ID}}">
  <div class="rc-flow-controls">
    <button class="rc-play-btn" onclick="(function(){
      var f=document.getElementById('{{ID}}');
      var stages=f.querySelectorAll('.rc-stage');
      var btn=f.querySelector('.rc-play-btn');
      btn.disabled=true;
      var i=0;
      function step(){if(i>=stages.length){btn.disabled=false;return;}
      show{{Name}}Stage(i+1);i++;setTimeout(step,1800);}step();
    })()">▶ Play</button>
    <button onclick="reset{{Name}}Flow()">Reset</button>
  </div>
  <div class="rc-flow-body">
    <div class="rc-flow-diagram">
      <div class="rc-stage" data-stage="1" onclick="show{{Name}}Stage(1)">
        <div class="rc-stage-title">① Stage Name</div>
        <div class="rc-stage-sub">key_function()</div>
      </div>
      <div class="rc-arrow">↓</div>
      <div class="rc-stage" data-stage="2" onclick="show{{Name}}Stage(2)">
        <div class="rc-stage-title">② Stage Name</div>
        <div class="rc-stage-sub">key_function()</div>
      </div>
      <!-- more stages + arrows -->
      <!-- add class="rc-stage rc-stage-loop" for stages with cyclic nature -->
    </div>
    <div class="rc-flow-detail">
      <div class="rc-detail-placeholder">← Click a stage or press Play</div>
    </div>
  </div>
  <div class="rc-progress">
    <div class="rc-progress-dot" data-dot="1"></div>
    <div class="rc-progress-dot" data-dot="2"></div>
  </div>
</div>

<script>
(function(){
  var data = [
    { title:'① Stage Name', section:'Section Ref',
      html:'Description with <code>function_name()</code>...',
      funcs:['func1()','func2()'] },
    { title:'② Stage Name', section:'Section Ref',
      html:'Description...',
      funcs:['func3()'] }
  ];
  window.show{{Name}}Stage = function(n) {
    var f = document.getElementById('{{ID}}');
    f.querySelectorAll('.rc-stage').forEach(function(s,i){
      s.classList.toggle('active', i===n-1);
    });
    f.querySelectorAll('.rc-arrow').forEach(function(a,i){
      a.classList.toggle('active', i===n-1 || i===n-2);
    });
    f.querySelectorAll('.rc-progress-dot').forEach(function(d,i){
      d.classList.remove('active','done');
      if(i<n-1) d.classList.add('done');
      else if(i===n-1) d.classList.add('active');
    });
    var d = data[n-1];
    f.querySelector('.rc-flow-detail').innerHTML = '<div class="rc-detail-content">'
      +'<h4>'+d.title+'</h4>'
      +'<div class="rc-detail-section">'+d.section+'</div>'
      +'<div class="rc-detail-text">'+d.html+'</div>'
      +'<div class="rc-detail-funcs">'
      +d.funcs.map(function(fn){return '<code>'+fn+'</code>';}).join('')
      +'</div></div>';
  };
  window.reset{{Name}}Flow = function() {
    var f = document.getElementById('{{ID}}');
    f.querySelectorAll('.rc-stage,.rc-arrow,.rc-progress-dot').forEach(function(e){
      e.classList.remove('active','done');
    });
    f.querySelector('.rc-flow-detail').innerHTML =
      '<div class="rc-detail-placeholder">← Click a stage or press Play</div>';
    f.querySelector('.rc-play-btn').disabled = false;
  };
})();
</script>
```

### CSS（如果 `custom.css` 中还没有 `.rc-flow`）

```css
/* === Interactive Flow Diagram (rc-flow) === */
.rc-flow {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-flow-controls {
    display: flex; gap: 8px; padding: 12px 16px;
    background: #f0f4f8; border-bottom: 1px solid #d0d7de;
}
.rc-flow-controls button {
    padding: 6px 18px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #2c3e50; font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.rc-flow-controls button:hover { background: #e8ecf1; }
.rc-flow-controls .rc-play-btn { background: #d97757; color: #fff; border-color: #c56a4a; }
.rc-flow-controls .rc-play-btn:hover { background: #c56a4a; }
.rc-flow-controls .rc-play-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.rc-flow-body { display: flex; flex-direction: column; gap: 0; }
@media (min-width: 768px) { .rc-flow-body { flex-direction: row; } }
.rc-flow-diagram {
    display: flex; flex-direction: column; align-items: center; padding: 20px 16px; gap: 0;
}
@media (min-width: 768px) {
    .rc-flow-diagram { flex: 0 0 320px; border-right: 1px solid #d0d7de; }
}
.rc-stage {
    width: 100%; max-width: 280px; padding: 12px 16px;
    border: 2px solid #d0d7de; border-radius: 8px; background: #f8f9fa;
    text-align: center; cursor: pointer; transition: all 0.3s ease; user-select: none;
}
.rc-stage:hover { border-color: #b0b8c4; background: #eef2f7; }
.rc-stage.active {
    border-color: #d97757; background: rgba(217,119,87,0.08);
    transform: scale(1.03); box-shadow: 0 2px 12px rgba(217,119,87,0.15);
}
.rc-stage-title { font-weight: 600; font-size: 14px; color: #1a1a2e; margin-bottom: 2px; }
.rc-stage.active .rc-stage-title { color: #d97757; }
.rc-stage-sub {
    font-size: 11px; color: #87867f;
    font-family: 'Cascadia Mono', 'JetBrains Mono', 'Fira Code', monospace;
}
.rc-stage-loop { position: relative; }
.rc-stage-loop::after {
    content: "↻"; position: absolute; top: 6px; right: 10px;
    font-size: 16px; color: #b0b8c4; transition: color 0.3s;
}
.rc-stage-loop.active::after { color: #d97757; }
.rc-arrow {
    font-size: 18px; color: #b0b8c4; line-height: 1; padding: 4px 0; transition: color 0.3s;
}
.rc-arrow.active { color: #d97757; }
.rc-flow-detail {
    flex: 1; min-height: 200px; padding: 20px;
    display: flex; flex-direction: column; justify-content: center;
    border-top: 1px solid #d0d7de;
}
@media (min-width: 768px) { .rc-flow-detail { border-top: none; } }
.rc-detail-placeholder { text-align: center; color: #87867f; font-size: 14px; font-style: italic; }
.rc-detail-content { animation: rc-fade-in 0.3s ease; }
@keyframes rc-fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.rc-detail-content h4 { margin: 0 0 4px 0; font-size: 16px; color: #d97757; font-weight: 600; }
.rc-detail-content .rc-detail-section {
    font-size: 12px; color: #87867f; margin-bottom: 10px;
    font-family: 'Cascadia Mono', 'JetBrains Mono', monospace;
}
.rc-detail-content .rc-detail-text { font-size: 14px; line-height: 1.7; color: #2c3e50; margin-bottom: 10px; }
.rc-detail-content .rc-detail-funcs { display: flex; flex-wrap: wrap; gap: 6px; }
.rc-detail-content .rc-detail-funcs code {
    font-size: 11px; padding: 2px 8px; background: #f0f2f5;
    border: 1px solid #e1e4e8; border-radius: 4px; color: #d63384;
    font-family: 'Cascadia Mono', 'JetBrains Mono', monospace;
}
.rc-progress {
    display: flex; gap: 4px; padding: 8px 16px;
    background: #f8f9fa; border-top: 1px solid #d0d7de; justify-content: center;
}
.rc-progress-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #d0d7de; transition: background 0.3s;
}
.rc-progress-dot.active { background: #d97757; }
.rc-progress-dot.done { background: #22c55e; }
/* Dark theme: Flow */
.navy .rc-flow, .coal .rc-flow { border-color: #30414e; }
.navy .rc-flow-controls, .coal .rc-flow-controls { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-flow-controls button, .coal .rc-flow-controls button { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-flow-controls button:hover, .coal .rc-flow-controls button:hover { background: #3a4a5a; }
.navy .rc-flow-controls .rc-play-btn, .coal .rc-flow-controls .rc-play-btn { background: #d97757; color: #fff; border-color: #c56a4a; }
.navy .rc-stage, .coal .rc-stage { border-color: #30414e; background: #1e2a3a; }
.navy .rc-stage:hover, .coal .rc-stage:hover { border-color: #4a5a6a; background: #2a3a4a; }
.navy .rc-stage.active, .coal .rc-stage.active { border-color: #d97757; background: rgba(217,119,87,0.12); }
.navy .rc-stage-title, .coal .rc-stage-title { color: #e0e0e0; }
.navy .rc-flow-diagram, .coal .rc-flow-diagram { border-right-color: #30414e; }
.navy .rc-flow-detail, .coal .rc-flow-detail { border-top-color: #30414e; }
.navy .rc-detail-content .rc-detail-text, .coal .rc-detail-content .rc-detail-text { color: #c9d1d9; }
.navy .rc-detail-content .rc-detail-funcs code, .coal .rc-detail-content .rc-detail-funcs code { background: #1e2a3a; border-color: #30414e; color: #f0a8c0; }
.navy .rc-detail-placeholder, .coal .rc-detail-placeholder { color: #6a737d; }
.navy .rc-progress, .coal .rc-progress { background: #1e2a3a; border-top-color: #30414e; }
.navy .rc-progress-dot, .coal .rc-progress-dot { background: #30414e; }
```

---

## 类型 ② 状态机图

适用于：多状态互相跳转、分支逻辑。

### HTML 模板

```html
<div class="rc-sm" id="{{ID}}">
  <div class="rc-sm-controls">
    <button onclick="reset{{Name}}SM()">Reset</button>
    <span class="rc-sm-hint">Click any state to see transitions</span>
  </div>
  <div class="rc-sm-body">
    <div class="rc-sm-diagram">
      <div class="rc-sm-state" data-state="1" onclick="show{{Name}}State(1)">
        <div class="rc-sm-label">State A</div>
      </div>
      <svg class="rc-sm-arrows" viewBox="0 0 400 300">
        <defs>
          <marker id="ah-{{ID}}" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#b0b8c4"/>
          </marker>
          <marker id="ah-a-{{ID}}" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
            <polygon points="0 0, 10 3.5, 0 7" fill="#d97757"/>
          </marker>
        </defs>
        <line class="rc-sm-edge" data-from="1" data-to="2" x1="100" y1="50" x2="300" y2="50"
              marker-end="url(#ah-{{ID}})"/>
      </svg>
    </div>
    <div class="rc-sm-detail">
      <div class="rc-detail-placeholder">← Click a state node</div>
    </div>
  </div>
</div>

<script>
(function(){
  var states = [
    { id:1, label:'State A',
      html:'<strong>State A</strong> description...',
      transitions:['→ State B: condition'] }
  ];
  window.show{{Name}}State = function(n) {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-sm-state').forEach(function(s){
      s.classList.toggle('active', parseInt(s.dataset.state)===n);
    });
    c.querySelectorAll('.rc-sm-edge').forEach(function(e){
      var isFrom = parseInt(e.dataset.from)===n;
      e.classList.toggle('active', isFrom);
      e.setAttribute('marker-end', isFrom ?
        'url(#ah-a-'+c.id+')' : 'url(#ah-'+c.id+')');
    });
    var s = states[n-1];
    c.querySelector('.rc-sm-detail').innerHTML = '<div class="rc-detail-content">'
      +'<h4>'+s.label+'</h4>'
      +'<div class="rc-detail-text">'+s.html+'</div>'
      +'<div class="rc-sm-transitions">'
      +s.transitions.map(function(t){return '<div class="rc-sm-trans">'+t+'</div>';}).join('')
      +'</div></div>';
  };
  window.reset{{Name}}SM = function() {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-sm-state,.rc-sm-edge').forEach(function(e){ e.classList.remove('active'); });
    c.querySelectorAll('.rc-sm-edge').forEach(function(e){
      e.setAttribute('marker-end','url(#ah-'+c.id+')');
    });
    c.querySelector('.rc-sm-detail').innerHTML =
      '<div class="rc-detail-placeholder">← Click a state node</div>';
  };
})();
</script>
```

### CSS（如果缺失 `.rc-sm`）

```css
/* === Interactive State Machine (rc-sm) === */
.rc-sm {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-sm-controls {
    display: flex; gap: 8px; align-items: center;
    padding: 12px 16px; background: #f0f4f8; border-bottom: 1px solid #d0d7de;
}
.rc-sm-controls button {
    padding: 6px 18px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #2c3e50; font-size: 13px; cursor: pointer; transition: all 0.2s;
}
.rc-sm-controls button:hover { background: #e8ecf1; }
.rc-sm-hint { font-size: 12px; color: #87867f; font-style: italic; }
.rc-sm-body { display: flex; flex-direction: column; }
@media (min-width: 768px) { .rc-sm-body { flex-direction: row; } }
.rc-sm-diagram {
    position: relative; display: flex; flex-wrap: wrap;
    justify-content: center; align-items: center;
    gap: 16px; padding: 24px 16px; min-height: 200px;
}
@media (min-width: 768px) {
    .rc-sm-diagram { flex: 0 0 360px; border-right: 1px solid #d0d7de; }
}
.rc-sm-diagram svg.rc-sm-arrows {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
}
.rc-sm-state {
    padding: 10px 20px; border: 2px solid #d0d7de; border-radius: 24px;
    background: #f8f9fa; cursor: pointer; transition: all 0.3s ease;
    user-select: none; z-index: 1; position: relative;
}
.rc-sm-state:hover { border-color: #b0b8c4; background: #eef2f7; }
.rc-sm-state.active {
    border-color: #d97757; background: rgba(217,119,87,0.08);
    transform: scale(1.05); box-shadow: 0 2px 12px rgba(217,119,87,0.15);
}
.rc-sm-label { font-weight: 600; font-size: 13px; color: #1a1a2e; }
.rc-sm-state.active .rc-sm-label { color: #d97757; }
.rc-sm-edge { stroke: #b0b8c4; stroke-width: 2; transition: stroke 0.3s; }
.rc-sm-edge.active { stroke: #d97757; stroke-width: 2.5; }
.rc-sm-detail {
    flex: 1; min-height: 180px; padding: 20px;
    display: flex; flex-direction: column; justify-content: center;
    border-top: 1px solid #d0d7de;
}
@media (min-width: 768px) { .rc-sm-detail { border-top: none; } }
.rc-sm-transitions { margin-top: 10px; }
.rc-sm-trans {
    padding: 4px 8px; margin: 4px 0; font-size: 13px;
    background: #f0f4f8; border-radius: 4px; color: #2c3e50;
    border-left: 3px solid #d97757;
}
/* Dark: State Machine */
.navy .rc-sm, .coal .rc-sm { border-color: #30414e; }
.navy .rc-sm-controls, .coal .rc-sm-controls { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-sm-controls button, .coal .rc-sm-controls button { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-sm-state, .coal .rc-sm-state { border-color: #30414e; background: #1e2a3a; }
.navy .rc-sm-state:hover, .coal .rc-sm-state:hover { border-color: #4a5a6a; background: #2a3a4a; }
.navy .rc-sm-state.active, .coal .rc-sm-state.active { border-color: #d97757; background: rgba(217,119,87,0.12); }
.navy .rc-sm-label, .coal .rc-sm-label { color: #e0e0e0; }
.navy .rc-sm-edge, .coal .rc-sm-edge { stroke: #4a5a6a; }
.navy .rc-sm-detail, .coal .rc-sm-detail { border-top-color: #30414e; }
.navy .rc-sm-diagram, .coal .rc-sm-diagram { border-right-color: #30414e; }
.navy .rc-sm-trans, .coal .rc-sm-trans { background: #1e2a3a; color: #c9d1d9; }
.navy .rc-sm-hint, .coal .rc-sm-hint { color: #6a737d; }
```

---

## 类型 ③ 前后对比图

适用于：新旧方案对比、有/无功能对比。

### HTML 模板

```html
<div class="rc-cmp" id="{{ID}}">
  <div class="rc-cmp-header">
    <button class="rc-cmp-tab active" data-tab="before" onclick="switch{{Name}}Tab('before')">
      Before
    </button>
    <button class="rc-cmp-tab" data-tab="after" onclick="switch{{Name}}Tab('after')">
      After
    </button>
    <button class="rc-cmp-tab" data-tab="diff" onclick="switch{{Name}}Tab('diff')">
      Diff
    </button>
  </div>
  <div class="rc-cmp-body">
    <div class="rc-cmp-panel" data-panel="before">
      <!-- before content -->
    </div>
    <div class="rc-cmp-panel" data-panel="after" style="display:none">
      <!-- after content -->
    </div>
    <div class="rc-cmp-panel" data-panel="diff" style="display:none">
      <div class="rc-cmp-diff">
        <div class="rc-cmp-col rc-cmp-col-old">
          <div class="rc-cmp-col-title">Before</div>
        </div>
        <div class="rc-cmp-col rc-cmp-col-new">
          <div class="rc-cmp-col-title">After</div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
(function(){
  window.switch{{Name}}Tab = function(tab) {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-cmp-tab').forEach(function(t){
      t.classList.toggle('active', t.dataset.tab===tab);
    });
    c.querySelectorAll('.rc-cmp-panel').forEach(function(p){
      p.style.display = p.dataset.panel===tab ? 'block' : 'none';
    });
  };
})();
</script>
```

### CSS（如果缺失 `.rc-cmp`）

```css
/* === Interactive Comparison (rc-cmp) === */
.rc-cmp {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-cmp-header { display: flex; background: #f0f4f8; border-bottom: 1px solid #d0d7de; }
.rc-cmp-tab {
    flex: 1; padding: 10px 16px; border: none; border-bottom: 3px solid transparent;
    background: transparent; color: #666; font-size: 14px; font-weight: 600;
    cursor: pointer; transition: all 0.2s;
}
.rc-cmp-tab:hover { background: #e8ecf1; }
.rc-cmp-tab.active { color: #d97757; border-bottom-color: #d97757; background: #fff; }
.rc-cmp-panel { padding: 20px; animation: rc-fade-in 0.3s ease; }
.rc-cmp-diff { display: flex; gap: 16px; flex-wrap: wrap; }
.rc-cmp-col { flex: 1; min-width: 250px; }
.rc-cmp-col-title {
    font-weight: 700; font-size: 13px; padding: 6px 10px; border-radius: 4px; margin-bottom: 8px;
}
.rc-cmp-col-old .rc-cmp-col-title { background: #fef2f2; color: #b91c1c; }
.rc-cmp-col-new .rc-cmp-col-title { background: #f0fdf4; color: #15803d; }
/* Dark: Comparison */
.navy .rc-cmp, .coal .rc-cmp { border-color: #30414e; }
.navy .rc-cmp-header, .coal .rc-cmp-header { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-cmp-tab, .coal .rc-cmp-tab { color: #8b949e; }
.navy .rc-cmp-tab.active, .coal .rc-cmp-tab.active { color: #d97757; background: #0d1117; }
.navy .rc-cmp-col-old .rc-cmp-col-title, .coal .rc-cmp-col-old .rc-cmp-col-title { background: #3b1c1c; color: #fca5a5; }
.navy .rc-cmp-col-new .rc-cmp-col-title, .coal .rc-cmp-col-new .rc-cmp-col-title { background: #1c3b2a; color: #86efac; }
```

---

## 类型 ④ 计算器/滑块

适用于：参数调节、预算分配、实时计算。

### HTML 模板

```html
<div class="rc-calc" id="{{ID}}">
  <div class="rc-calc-header">
    <h4 class="rc-calc-title">Title</h4>
    <button class="rc-calc-reset" onclick="reset{{Name}}Calc()">Reset</button>
  </div>
  <div class="rc-calc-body">
    <div class="rc-calc-inputs">
      <div class="rc-calc-field">
        <label>Param <span class="rc-calc-val" id="{{ID}}-v1">50</span></label>
        <input type="range" min="0" max="100" value="50"
               oninput="update{{Name}}Calc()">
      </div>
    </div>
    <div class="rc-calc-result">
      <div class="rc-calc-output" id="{{ID}}-output"></div>
    </div>
  </div>
</div>

<script>
(function(){
  window.update{{Name}}Calc = function() {
    var c = document.getElementById('{{ID}}');
    var inputs = c.querySelectorAll('input[type=range]');
    var vals = Array.prototype.map.call(inputs, function(inp){ return parseInt(inp.value); });
    // update value displays
    c.querySelectorAll('.rc-calc-val').forEach(function(v,i){ v.textContent = vals[i]; });
    // compute and render result
    c.querySelector('.rc-calc-output').innerHTML = 'Result: ' + vals.join(', ');
  };
  window.reset{{Name}}Calc = function() {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('input[type=range]').forEach(function(inp){ inp.value = inp.defaultValue; });
    update{{Name}}Calc();
  };
  update{{Name}}Calc(); // initial render
})();
</script>
```

### CSS（如果缺失 `.rc-calc`）

```css
/* === Interactive Calculator (rc-calc) === */
.rc-calc {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-calc-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px; background: #f0f4f8; border-bottom: 1px solid #d0d7de;
}
.rc-calc-title { margin: 0; font-size: 15px; color: #1a1a2e; }
.rc-calc-reset {
    padding: 4px 14px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #2c3e50; font-size: 12px; cursor: pointer;
}
.rc-calc-reset:hover { background: #e8ecf1; }
.rc-calc-body { padding: 20px; display: flex; flex-direction: column; gap: 20px; }
@media (min-width: 768px) { .rc-calc-body { flex-direction: row; } }
.rc-calc-inputs { flex: 1; display: flex; flex-direction: column; gap: 14px; }
.rc-calc-field label {
    display: flex; justify-content: space-between; font-size: 13px;
    font-weight: 600; color: #2c3e50; margin-bottom: 4px;
}
.rc-calc-val { font-family: 'Cascadia Mono', monospace; color: #d97757; font-weight: 700; }
.rc-calc-field input[type=range] { width: 100%; accent-color: #d97757; height: 6px; }
.rc-calc-result {
    flex: 1; padding: 16px; background: #f8f9fa; border: 1px solid #e1e4e8;
    border-radius: 8px; min-height: 100px;
}
@media (min-width: 768px) {
    .rc-calc-inputs { flex: 0 0 45%; border-right: 1px solid #d0d7de; padding-right: 20px; }
}
.rc-calc-output { font-size: 14px; line-height: 1.7; color: #2c3e50; }
.rc-calc-output .rc-calc-bar {
    height: 24px; border-radius: 4px; margin: 4px 0; transition: width 0.3s ease;
    background: #d97757; opacity: 0.8;
}
/* Dark: Calculator */
.navy .rc-calc, .coal .rc-calc { border-color: #30414e; }
.navy .rc-calc-header, .coal .rc-calc-header { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-calc-title, .coal .rc-calc-title { color: #e0e0e0; }
.navy .rc-calc-reset, .coal .rc-calc-reset { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-calc-field label, .coal .rc-calc-field label { color: #c9d1d9; }
.navy .rc-calc-result, .coal .rc-calc-result { background: #1e2a3a; border-color: #30414e; }
.navy .rc-calc-output, .coal .rc-calc-output { color: #c9d1d9; }
.navy .rc-calc-inputs, .coal .rc-calc-inputs { border-right-color: #30414e; }
```

---

## 类型 ⑤ 树形展开图

适用于：目录结构、配置层级、AST。

### HTML 模板

```html
<div class="rc-tree" id="{{ID}}">
  <div class="rc-tree-controls">
    <button onclick="expandAll{{Name}}()">Expand All</button>
    <button onclick="collapseAll{{Name}}()">Collapse All</button>
  </div>
  <div class="rc-tree-body">
    <ul class="rc-tree-list">
      <li class="rc-tree-node rc-tree-expandable" onclick="toggle{{Name}}Node(event, this)">
        <span class="rc-tree-icon">▶</span>
        <span class="rc-tree-label">Parent</span>
        <span class="rc-tree-badge">3</span>
        <ul class="rc-tree-children" style="display:none">
          <li class="rc-tree-node rc-tree-leaf" onclick="show{{Name}}Leaf(event, this)"
              data-info='Leaf description here'>
            <span class="rc-tree-icon">📄</span>
            <span class="rc-tree-label">Child</span>
          </li>
        </ul>
      </li>
    </ul>
    <div class="rc-tree-detail">
      <div class="rc-detail-placeholder">← Click a leaf node</div>
    </div>
  </div>
</div>

<script>
(function(){
  window.toggle{{Name}}Node = function(e, el) {
    if(e.target.closest('.rc-tree-children')) return;
    var ch = el.querySelector('.rc-tree-children');
    if(!ch) return;
    var icon = el.querySelector(':scope > .rc-tree-icon');
    if(ch.style.display==='none'){ ch.style.display='block'; icon.textContent='▼'; el.classList.add('expanded'); }
    else { ch.style.display='none'; icon.textContent='▶'; el.classList.remove('expanded'); }
    e.stopPropagation();
  };
  window.show{{Name}}Leaf = function(e, el) {
    e.stopPropagation();
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-tree-leaf').forEach(function(l){ l.classList.remove('active'); });
    el.classList.add('active');
    c.querySelector('.rc-tree-detail').innerHTML =
      '<div class="rc-detail-content"><div class="rc-detail-text">'
      +(el.dataset.info||el.querySelector('.rc-tree-label').textContent)
      +'</div></div>';
  };
  window.expandAll{{Name}} = function() {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-tree-children').forEach(function(ch){ ch.style.display='block'; });
    c.querySelectorAll('.rc-tree-expandable > .rc-tree-icon').forEach(function(i){ i.textContent='▼'; });
  };
  window.collapseAll{{Name}} = function() {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-tree-children').forEach(function(ch){ ch.style.display='none'; });
    c.querySelectorAll('.rc-tree-expandable > .rc-tree-icon').forEach(function(i){ i.textContent='▶'; });
  };
})();
</script>
```

### CSS（如果缺失 `.rc-tree`）

```css
/* === Interactive Tree (rc-tree) === */
.rc-tree {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-tree-controls {
    display: flex; gap: 8px; padding: 12px 16px;
    background: #f0f4f8; border-bottom: 1px solid #d0d7de;
}
.rc-tree-controls button {
    padding: 4px 14px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #2c3e50; font-size: 12px; cursor: pointer;
}
.rc-tree-controls button:hover { background: #e8ecf1; }
.rc-tree-body { display: flex; flex-direction: column; }
@media (min-width: 768px) { .rc-tree-body { flex-direction: row; } }
.rc-tree-list {
    list-style: none; margin: 0; padding: 16px; font-size: 13px; line-height: 1.8;
}
@media (min-width: 768px) {
    .rc-tree-list { flex: 0 0 50%; border-right: 1px solid #d0d7de; overflow-y: auto; max-height: 400px; }
}
.rc-tree-list ul { list-style: none; padding-left: 20px; }
.rc-tree-node { cursor: pointer; padding: 2px 4px; border-radius: 4px; }
.rc-tree-node:hover { background: #f0f4f8; }
.rc-tree-leaf.active { background: rgba(217,119,87,0.08); }
.rc-tree-icon { display: inline-block; width: 18px; font-size: 11px; color: #87867f; transition: transform 0.2s; }
.rc-tree-label { font-weight: 500; color: #1a1a2e; }
.rc-tree-leaf.active .rc-tree-label { color: #d97757; font-weight: 600; }
.rc-tree-badge {
    font-size: 11px; color: #87867f; background: #e8ecf1;
    padding: 1px 6px; border-radius: 10px; margin-left: 6px;
}
.rc-tree-detail {
    flex: 1; min-height: 150px; padding: 20px;
    display: flex; align-items: flex-start; justify-content: center;
    border-top: 1px solid #d0d7de;
}
@media (min-width: 768px) { .rc-tree-detail { border-top: none; } }
/* Dark: Tree */
.navy .rc-tree, .coal .rc-tree { border-color: #30414e; }
.navy .rc-tree-controls, .coal .rc-tree-controls { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-tree-controls button, .coal .rc-tree-controls button { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-tree-list, .coal .rc-tree-list { border-right-color: #30414e; }
.navy .rc-tree-node:hover, .coal .rc-tree-node:hover { background: #2a3a4a; }
.navy .rc-tree-label, .coal .rc-tree-label { color: #e0e0e0; }
.navy .rc-tree-badge, .coal .rc-tree-badge { background: #2a3a4a; color: #8b949e; }
.navy .rc-tree-detail, .coal .rc-tree-detail { border-top-color: #30414e; }
```

---

## 类型 ⑥ 序列图

适用于：多角色时序交互（API 请求/响应、消息流）。

### HTML 模板

```html
<div class="rc-seq" id="{{ID}}">
  <div class="rc-seq-controls">
    <button class="rc-play-btn" onclick="play{{Name}}Seq()">▶ Play</button>
    <button onclick="reset{{Name}}Seq()">Reset</button>
    <span class="rc-seq-counter" id="{{ID}}-counter"></span>
  </div>
  <div class="rc-seq-body">
    <div class="rc-seq-header">
      <div class="rc-seq-actor">Actor A</div>
      <div class="rc-seq-actor">Actor B</div>
      <div class="rc-seq-actor">Actor C</div>
    </div>
    <div class="rc-seq-lifelines">
      <div class="rc-seq-msg" data-step="1" onclick="show{{Name}}Step(1)">
        <div class="rc-seq-msg-arrow"></div>
        <div class="rc-seq-msg-label">Request</div>
      </div>
      <div class="rc-seq-msg rc-seq-msg-return" data-step="2" onclick="show{{Name}}Step(2)">
        <div class="rc-seq-msg-arrow"></div>
        <div class="rc-seq-msg-label">Response</div>
      </div>
    </div>
    <div class="rc-seq-detail">
      <div class="rc-detail-placeholder">← Click a message or press Play</div>
    </div>
  </div>
</div>

<script>
(function(){
  var steps = [
    { label:'Request', html:'Description...', from:'Actor A', to:'Actor B' },
    { label:'Response', html:'Description...', from:'Actor B', to:'Actor A' }
  ];
  var timer = null;
  window.show{{Name}}Step = function(n) {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-seq-msg').forEach(function(m){
      var s = parseInt(m.dataset.step);
      m.classList.toggle('active', s===n);
      m.classList.toggle('done', s<n);
    });
    document.getElementById('{{ID}}-counter').textContent = n+' / '+steps.length;
    var d = steps[n-1];
    c.querySelector('.rc-seq-detail').innerHTML = '<div class="rc-detail-content">'
      +'<h4>'+d.from+' → '+d.to+'</h4>'
      +'<div class="rc-detail-text">'+d.html+'</div></div>';
  };
  window.play{{Name}}Seq = function() {
    var c = document.getElementById('{{ID}}');
    var btn = c.querySelector('.rc-play-btn');
    btn.disabled = true; var i = 0;
    function step(){ if(i>=steps.length){btn.disabled=false;return;}
      show{{Name}}Step(i+1); i++; timer=setTimeout(step,1500); } step();
  };
  window.reset{{Name}}Seq = function() {
    if(timer) clearTimeout(timer);
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-seq-msg').forEach(function(m){ m.classList.remove('active','done'); });
    c.querySelector('.rc-seq-detail').innerHTML =
      '<div class="rc-detail-placeholder">← Click a message or press Play</div>';
    c.querySelector('.rc-play-btn').disabled = false;
    document.getElementById('{{ID}}-counter').textContent = '';
  };
})();
</script>
```

### CSS（如果缺失 `.rc-seq`）

```css
/* === Interactive Sequence Diagram (rc-seq) === */
.rc-seq {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-seq-controls {
    display: flex; gap: 8px; align-items: center;
    padding: 12px 16px; background: #f0f4f8; border-bottom: 1px solid #d0d7de;
}
.rc-seq-controls button {
    padding: 6px 18px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #2c3e50; font-size: 13px; cursor: pointer;
}
.rc-seq-controls button:hover { background: #e8ecf1; }
.rc-seq-controls .rc-play-btn { background: #d97757; color: #fff; border-color: #c56a4a; }
.rc-seq-controls .rc-play-btn:hover { background: #c56a4a; }
.rc-seq-controls .rc-play-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.rc-seq-counter { font-size: 12px; color: #87867f; margin-left: auto; }
.rc-seq-body { display: flex; flex-direction: column; }
@media (min-width: 768px) { .rc-seq-body { flex-direction: row; } }
.rc-seq-header {
    display: flex; justify-content: space-around; padding: 12px 16px 0;
}
.rc-seq-actor {
    padding: 8px 20px; background: #e8ecf1; border: 2px solid #d0d7de;
    border-radius: 6px; font-weight: 700; font-size: 13px; color: #1a1a2e;
    text-align: center; min-width: 70px;
}
.rc-seq-lifelines { padding: 8px 16px 16px; display: flex; flex-direction: column; gap: 6px; }
@media (min-width: 768px) {
    .rc-seq-header, .rc-seq-lifelines { flex: 0 0 400px; }
    .rc-seq-lifelines { border-right: 1px solid #d0d7de; }
}
.rc-seq-msg {
    display: flex; align-items: center; gap: 8px;
    padding: 6px 12px; border-radius: 6px; cursor: pointer;
    border-left: 3px solid transparent; transition: all 0.3s;
}
.rc-seq-msg:hover { background: #f0f4f8; }
.rc-seq-msg.active { background: rgba(217,119,87,0.08); border-left-color: #d97757; }
.rc-seq-msg.done { opacity: 0.5; }
.rc-seq-msg-arrow { font-size: 14px; color: #b0b8c4; }
.rc-seq-msg.active .rc-seq-msg-arrow { color: #d97757; }
.rc-seq-msg-label { font-size: 13px; color: #2c3e50; }
.rc-seq-msg.active .rc-seq-msg-label { color: #d97757; font-weight: 600; }
.rc-seq-msg-return .rc-seq-msg-arrow::before { content: "\2190 "; }
.rc-seq-msg:not(.rc-seq-msg-return) .rc-seq-msg-arrow::before { content: "\2192 "; }
.rc-seq-detail {
    flex: 1; min-height: 150px; padding: 20px;
    display: flex; flex-direction: column; justify-content: center;
    border-top: 1px solid #d0d7de;
}
@media (min-width: 768px) { .rc-seq-detail { border-top: none; } }
/* Dark: Sequence */
.navy .rc-seq, .coal .rc-seq { border-color: #30414e; }
.navy .rc-seq-controls, .coal .rc-seq-controls { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-seq-controls button, .coal .rc-seq-controls button { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-seq-controls .rc-play-btn, .coal .rc-seq-controls .rc-play-btn { background: #d97757; color: #fff; }
.navy .rc-seq-actor, .coal .rc-seq-actor { background: #2a3a4a; border-color: #30414e; color: #e0e0e0; }
.navy .rc-seq-msg:hover, .coal .rc-seq-msg:hover { background: #2a3a4a; }
.navy .rc-seq-msg-label, .coal .rc-seq-msg-label { color: #c9d1d9; }
.navy .rc-seq-lifelines, .coal .rc-seq-lifelines { border-right-color: #30414e; }
.navy .rc-seq-detail, .coal .rc-seq-detail { border-top-color: #30414e; }
```

---

## 类型 ⑦ 时间线

适用于：版本演进、生命周期、里程碑。

### HTML 模板

```html
<div class="rc-tl" id="{{ID}}">
  <div class="rc-tl-header"><h4 class="rc-tl-title">Title</h4></div>
  <div class="rc-tl-body">
    <div class="rc-tl-track">
      <div class="rc-tl-item" data-step="1" onclick="show{{Name}}TL(1)">
        <div class="rc-tl-marker"></div>
        <div class="rc-tl-content">
          <div class="rc-tl-time">T=0</div>
          <div class="rc-tl-label">Phase Name</div>
        </div>
      </div>
    </div>
    <div class="rc-tl-detail">
      <div class="rc-detail-placeholder">← Click a time point</div>
    </div>
  </div>
</div>

<script>
(function(){
  var data = [
    { time:'T=0', label:'Phase', html:'Description...' }
  ];
  window.show{{Name}}TL = function(n) {
    var c = document.getElementById('{{ID}}');
    c.querySelectorAll('.rc-tl-item').forEach(function(item,i){
      item.classList.toggle('active', i===n-1);
      item.classList.toggle('done', i<n-1);
    });
    var d = data[n-1];
    c.querySelector('.rc-tl-detail').innerHTML = '<div class="rc-detail-content">'
      +'<h4>'+d.time+' — '+d.label+'</h4>'
      +'<div class="rc-detail-text">'+d.html+'</div></div>';
  };
})();
</script>
```

### CSS（如果缺失 `.rc-tl`）

```css
/* === Interactive Timeline (rc-tl) === */
.rc-tl {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-tl-header { padding: 12px 16px; background: #f0f4f8; border-bottom: 1px solid #d0d7de; }
.rc-tl-title { margin: 0; font-size: 15px; color: #1a1a2e; }
.rc-tl-body { display: flex; flex-direction: column; }
@media (min-width: 768px) { .rc-tl-body { flex-direction: row; } }
.rc-tl-track { padding: 20px 16px 20px 40px; position: relative; }
@media (min-width: 768px) { .rc-tl-track { flex: 0 0 320px; border-right: 1px solid #d0d7de; } }
.rc-tl-track::before {
    content: ''; position: absolute; left: 26px; top: 20px; bottom: 20px;
    width: 3px; background: #d0d7de; border-radius: 3px;
}
.rc-tl-item {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 8px 0; cursor: pointer; position: relative; transition: all 0.3s;
}
.rc-tl-item:hover .rc-tl-label { color: #d97757; }
.rc-tl-marker {
    width: 14px; height: 14px; border-radius: 50%;
    background: #d0d7de; border: 3px solid #fff; box-shadow: 0 0 0 2px #d0d7de;
    flex-shrink: 0; margin-top: 3px; transition: all 0.3s; position: relative; z-index: 1;
}
.rc-tl-item.active .rc-tl-marker {
    background: #d97757; box-shadow: 0 0 0 2px #d97757, 0 0 8px rgba(217,119,87,0.3);
}
.rc-tl-item.done .rc-tl-marker { background: #22c55e; box-shadow: 0 0 0 2px #22c55e; }
.rc-tl-time { font-size: 11px; color: #87867f; font-family: 'Cascadia Mono', monospace; margin-bottom: 2px; }
.rc-tl-label { font-size: 14px; font-weight: 600; color: #1a1a2e; transition: color 0.3s; }
.rc-tl-item.active .rc-tl-label { color: #d97757; }
.rc-tl-detail {
    flex: 1; min-height: 150px; padding: 20px;
    display: flex; flex-direction: column; justify-content: center;
    border-top: 1px solid #d0d7de;
}
@media (min-width: 768px) { .rc-tl-detail { border-top: none; } }
/* Dark: Timeline */
.navy .rc-tl, .coal .rc-tl { border-color: #30414e; }
.navy .rc-tl-header, .coal .rc-tl-header { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-tl-title, .coal .rc-tl-title { color: #e0e0e0; }
.navy .rc-tl-track::before, .coal .rc-tl-track::before { background: #30414e; }
.navy .rc-tl-track, .coal .rc-tl-track { border-right-color: #30414e; }
.navy .rc-tl-marker, .coal .rc-tl-marker { background: #30414e; border-color: #0d1117; box-shadow: 0 0 0 2px #30414e; }
.navy .rc-tl-label, .coal .rc-tl-label { color: #e0e0e0; }
.navy .rc-tl-detail, .coal .rc-tl-detail { border-top-color: #30414e; }
```

---

## 类型 ⑧ 交互式模拟器

适用于：流程模拟、场景演练、交互式教学。

### HTML 模板

```html
<div class="rc-sim" id="{{ID}}">
  <div class="rc-sim-header">
    <h4 class="rc-sim-title">Title</h4>
    <button class="rc-sim-reset" onclick="reset{{Name}}Sim()">Reset</button>
  </div>
  <div class="rc-sim-body">
    <div class="rc-sim-input">
      <div class="rc-sim-scenario">
        <label>Scenario:</label>
        <select onchange="set{{Name}}Scenario(this.value)">
          <option value="0">Scenario A</option>
          <option value="1">Scenario B</option>
        </select>
      </div>
      <div class="rc-sim-action">
        <button class="rc-play-btn" onclick="run{{Name}}Sim()">▶ Run</button>
      </div>
    </div>
    <div class="rc-sim-output">
      <div class="rc-sim-console">
        <div class="rc-detail-placeholder">Select a scenario and click Run</div>
      </div>
    </div>
  </div>
</div>

<script>
(function(){
  var scenarios = [
    { name:'Scenario A', steps:[
      { actor:'System', text:'Initializing...' },
      { actor:'Agent', text:'Processing...' },
      { actor:'Result', text:'Done' }
    ]}
  ];
  var timer = null;
  window.set{{Name}}Scenario = function(idx) { reset{{Name}}Sim(); };
  window.run{{Name}}Sim = function() {
    var c = document.getElementById('{{ID}}');
    var idx = parseInt(c.querySelector('select').value);
    var sc = scenarios[idx];
    var con = c.querySelector('.rc-sim-console');
    con.innerHTML = '<div class="rc-sim-log-header">▶ '+sc.name+'</div>';
    var btn = c.querySelector('.rc-play-btn'); btn.disabled = true;
    var i = 0;
    function step() {
      if(i>=sc.steps.length){ btn.disabled=false; return; }
      var s = sc.steps[i];
      var line = document.createElement('div');
      line.className = 'rc-sim-log-line';
      line.innerHTML = '<span class="rc-sim-actor">'+s.actor+'</span> '+s.text;
      con.appendChild(line);
      line.style.animation = 'rc-fade-in 0.3s ease';
      i++; timer = setTimeout(step, 800);
    } step();
  };
  window.reset{{Name}}Sim = function() {
    if(timer) clearTimeout(timer);
    var c = document.getElementById('{{ID}}');
    c.querySelector('.rc-sim-console').innerHTML =
      '<div class="rc-detail-placeholder">Select a scenario and click Run</div>';
    c.querySelector('.rc-play-btn').disabled = false;
  };
})();
</script>
```

### CSS（如果缺失 `.rc-sim`）

```css
/* === Interactive Simulator (rc-sim) === */
.rc-sim {
    margin: 1.5em 0; border: 1px solid #d0d7de; border-radius: 8px;
    overflow: hidden; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}
.rc-sim-header {
    display: flex; justify-content: space-between; align-items: center;
    padding: 12px 16px; background: #f0f4f8; border-bottom: 1px solid #d0d7de;
}
.rc-sim-title { margin: 0; font-size: 15px; color: #1a1a2e; }
.rc-sim-reset {
    padding: 4px 14px; border: 1px solid #d0d7de; border-radius: 6px;
    background: #fff; color: #2c3e50; font-size: 12px; cursor: pointer;
}
.rc-sim-reset:hover { background: #e8ecf1; }
.rc-sim-body { display: flex; flex-direction: column; }
@media (min-width: 768px) { .rc-sim-body { flex-direction: row; } }
.rc-sim-input { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
@media (min-width: 768px) { .rc-sim-input { flex: 0 0 240px; border-right: 1px solid #d0d7de; } }
.rc-sim-scenario label { font-size: 13px; font-weight: 600; color: #2c3e50; display: block; margin-bottom: 4px; }
.rc-sim-scenario select {
    width: 100%; padding: 6px 10px; border: 1px solid #d0d7de; border-radius: 6px;
    font-size: 13px; background: #fff; color: #2c3e50;
}
.rc-sim-output { flex: 1; }
.rc-sim-console {
    min-height: 200px; padding: 16px;
    background: #1a1a2e; color: #e0e0e0; font-family: 'Cascadia Mono', monospace;
    font-size: 13px; line-height: 1.8; overflow-y: auto; max-height: 350px;
}
.rc-sim-console .rc-detail-placeholder { color: #6a737d; font-style: italic; }
.rc-sim-log-header { color: #d97757; font-weight: 700; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #333; }
.rc-sim-log-line { padding: 2px 0; }
.rc-sim-actor { display: inline-block; min-width: 60px; color: #87ceeb; font-weight: 600; margin-right: 8px; }
/* Dark: Simulator */
.navy .rc-sim, .coal .rc-sim { border-color: #30414e; }
.navy .rc-sim-header, .coal .rc-sim-header { background: #1e2a3a; border-bottom-color: #30414e; }
.navy .rc-sim-title, .coal .rc-sim-title { color: #e0e0e0; }
.navy .rc-sim-reset, .coal .rc-sim-reset { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-sim-input, .coal .rc-sim-input { border-right-color: #30414e; }
.navy .rc-sim-scenario label, .coal .rc-sim-scenario label { color: #c9d1d9; }
.navy .rc-sim-scenario select, .coal .rc-sim-scenario select { background: #2a3a4a; border-color: #30414e; color: #c9d1d9; }
.navy .rc-sim-console, .coal .rc-sim-console { background: #0d1117; }
```
