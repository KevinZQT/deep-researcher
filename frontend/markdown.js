// Small DOM-based renderer: model HTML stays text; only http(s) links are clickable.
function renderMarkdown(markdown, target) {
  target.replaceChildren();
  const inline = (text, parent) => {
    const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^\s)]+\))/g;
    let start = 0;
    for (const match of text.matchAll(pattern)) {
      parent.append(document.createTextNode(text.slice(start, match.index)));
      const token = match[0];
      if (token.startsWith('`')) {
        const code = document.createElement('code'); code.textContent = token.slice(1,-1); parent.append(code);
      } else if (token.startsWith('**')) {
        const strong = document.createElement('strong'); strong.textContent = token.slice(2,-2); parent.append(strong);
      } else {
        const parts = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
        let url; try { url = new URL(parts[2]); } catch {}
        if (url && ['http:', 'https:'].includes(url.protocol)) {
          const a = document.createElement('a'); a.textContent = parts[1]; a.href = url.href;
          a.target = '_blank'; a.rel = 'noopener noreferrer'; parent.append(a);
        } else parent.append(document.createTextNode(token));
      }
      start = match.index + token.length;
    }
    parent.append(document.createTextNode(text.slice(start)));
  };
  const lines = markdown.replace(/\r\n?/g,'\n').split('\n');
  const cells = line => line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(cell=>cell.trim());
  let list = null;
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i], trimmed = line.trim();
    if (!trimmed) { list = null; continue; }
    if (trimmed.startsWith('```')) {
      list = null; const pre=document.createElement('pre'), code=document.createElement('code'), body=[];
      while (++i < lines.length && !lines[i].trim().startsWith('```')) body.push(lines[i]);
      code.textContent=body.join('\n'); pre.append(code); target.append(pre); continue;
    }
    if (line.includes('|') && i+1 < lines.length && cells(lines[i+1]).every(cell=>/^:?-{3,}:?$/.test(cell))) {
      list=null; const wrap=document.createElement('div'); wrap.className='table-scroll';
      const table=document.createElement('table'), head=document.createElement('thead'), body=document.createElement('tbody');
      const row=(values,tag,container)=>{const tr=document.createElement('tr');for(const value of values){const cell=document.createElement(tag);inline(value,cell);tr.append(cell);}container.append(tr);};
      row(cells(line),'th',head);i++;
      while(i+1<lines.length && lines[i+1].includes('|') && lines[i+1].trim())row(cells(lines[++i]),'td',body);
      table.append(head,body);wrap.append(table);target.append(wrap);continue;
    }
    const heading=line.match(/^(#{1,6})\s+(.+)$/);
    if(heading){list=null;const node=document.createElement('h'+heading[1].length);inline(heading[2],node);target.append(node);continue;}
    if(/^\s*([-*_])(?:\s*\1){2,}\s*$/.test(line)){list=null;target.append(document.createElement('hr'));continue;}
    const item=line.match(/^\s*(?:([-*+])|\d+[.)])\s+(.+)$/);
    if(item){const tag=item[1]?'UL':'OL';if(!list||list.tagName!==tag){list=document.createElement(tag.toLowerCase());target.append(list);}const li=document.createElement('li');inline(item[2],li);list.append(li);continue;}
    list=null;
    const node=document.createElement(trimmed.startsWith('> ')?'blockquote':'p');
    inline(trimmed.startsWith('> ')?trimmed.slice(2):line,node);target.append(node);
  }
}
