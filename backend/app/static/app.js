document.addEventListener('DOMContentLoaded', ()=>{
  const statusEl = document.getElementById('status');
  const listEl = document.getElementById('summaries');

  let summaries = [];

  async function load(){
    const url = typeof API_ENDPOINT !== 'undefined' ? API_ENDPOINT : '/summaries';
    statusEl.textContent = 'Loading...';
    listEl.innerHTML = '';
    try{
      const res = await fetch(url);
      if(!res.ok) throw new Error(`${res.status} ${res.statusText}`);
      const data = await res.json();
      summaries = Array.isArray(data)? data : [data];
      render(summaries);
      statusEl.textContent = `Loaded ${summaries.length} summaries.`;
    }catch(err){
      statusEl.textContent = 'Error: '+err.message;
      listEl.innerHTML = '<div class="empty card">Unable to load summaries. Check the endpoint or CORS settings.</div>';
    }
  }

  function render(items){
    if(!items || items.length === 0){
      listEl.innerHTML = '<div class="empty card">No summaries found.</div>';
      return;
    }

    listEl.innerHTML = '';
    items.forEach(item => listEl.appendChild(createCard(item)));
  }

  function parseDate(item){
    const raw = item.date || item.created_at || item.createdAt || item.timestamp || item.published_date || item.authored_at;
    if(!raw) return null;
    if(raw instanceof Date) return raw;
    const date = typeof raw === 'number' ? new Date(raw) : new Date(raw.toString());
    return Number.isNaN(date.getTime()) ? null : date;
  }

  function formatDate(raw){
    const date = parseDate({date: raw});
    if(!date) return raw || 'Unknown date';
    const day = String(date.getDate()).padStart(2,'0');
    const month = String(date.getMonth() + 1).padStart(2,'0');
    const year = date.getFullYear();
    const hours = String(date.getHours()).padStart(2,'0');
    const minutes = String(date.getMinutes()).padStart(2,'0');
    return `${day}-${month}-${year} ${hours}:${minutes}`;
  }

  function getListItems(item){
    return item.assignments || item.exercises || item.items || item.program || item.summary_points || [];
  }

  function renderList(values){
    const list = document.createElement('ul');
    list.className = 'card-list';
    values.forEach(value => {
      const text = typeof value === 'object'
        ? value.name || value.title || value.label || JSON.stringify(value)
        : value;
      if(text){
        const li = document.createElement('li');
        li.textContent = text;
        list.appendChild(li);
      }
    });
    return list;
  }

  function createCard(item){
    const card = document.createElement('article');
    card.className = 'card';

    const header = document.createElement('div');
    header.className = 'card-header';

    const title = document.createElement('h2');
    title.className = 'card-title';
    title.textContent = item.summary_title || item.title || 'AI Summary Notes';

    const date = document.createElement('div');
    date.className = 'card-date';
    date.textContent = formatDate(item.stored_at || item.date || item.created_at || item.authored_at || item.timestamp || item.published_date || item.authored_at);

    header.appendChild(title);
    header.appendChild(date);
    card.appendChild(header);

    const meta = document.createElement('div');
    meta.className = 'card-meta';
    meta.appendChild(metaItem('Progress', item.patient_progress || 'Not reported'));
    meta.appendChild(metaItem('Pain level', item.pain_level || 'Not reported'));
    meta.appendChild(metaItem('Functional status', item.functional_status || 'Not reported'));
    card.appendChild(meta);

    const body = document.createElement('div');
    body.className = 'card-body';
    const heading = document.createElement('h3');
    heading.className = 'summary-heading';
    heading.textContent = 'Summary';
    body.appendChild(heading);

    const summary = document.createElement('p');
    summary.textContent = item.clinical_summary || item.summary || 'No clinical summary available.';
    body.appendChild(summary);
    card.appendChild(body);

    return card;
  }

  function metaItem(label, value){
    const box = document.createElement('div');
    box.className = 'meta-item';
    const lab = document.createElement('div'); lab.className = 'label'; lab.textContent = label;
    const val = document.createElement('div'); val.className = 'value'; val.textContent = value ? value : 'Not reported';
    box.appendChild(lab);
    box.appendChild(val);
    return box;
  }

  load();
});
