(function(){
  var VALID_TABS={overview:1,jails:1,banned:1,whitelist:1,blacklist:1,logs:1,statistics:1,settings:1};
  var bannedState={page:1,pageSize:50,q:'',total:0,pages:1,loading:false};
  var wlState={page:1,pageSize:50,q:'',all:[],filtered:[]};
  var syncRunning=false;
  window.F2B=window.F2B||{};

  function toast(msg){var el=document.getElementById('f2bToast');el.textContent=msg;el.style.display='block';clearTimeout(el._t);el._t=setTimeout(function(){el.style.display='none';},3500);}
  function esc(s){return String(s||'').replace(/[&<>"']/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]);});}
  function getCookie(name){
    var m=document.cookie.match(new RegExp('(?:^|; )'+name.replace(/([.$?*|{}()[\]\\/+^])/g,'\\$1')+'=([^;]*)'));
    return m?decodeURIComponent(m[1]):'';
  }
  async function api(url, opts){
    opts=opts||{};
    var method=(opts.method||'GET').toUpperCase();
    var headers={
      'X-CSRFToken':getCookie('csrftoken')||'',
      'X-Requested-With':'XMLHttpRequest'
    };
    if(method!=='GET' && method!=='HEAD'){
      headers['Content-Type']='application/json';
    }
    var res=await fetch(url, Object.assign({}, opts, {
      credentials:'include',
      headers:Object.assign(headers, opts.headers||{})
    }));
    var ct=(res.headers.get('content-type')||'');
    var text=await res.text();
    var data=null;
    if(ct.indexOf('application/json')!==-1 || (text&&text.charAt(0)==='{' )){
      try{ data=JSON.parse(text); }catch(e){ throw new Error('Invalid JSON from '+url); }
    } else {
      throw new Error('Non-JSON response ('+res.status+') from '+url+'. Try refreshing / logging in again.');
    }
    if(!res.ok || (data && data.login_required)){
      var err=(data && (data.error||data.error_message||data.errorMessage)) || ('HTTP '+res.status);
      if(data && data.login_required){
        throw new Error(err+' Refresh the page and log in again if needed.');
      }
      throw new Error(err);
    }
    return data;
  }
  window.F2B.api=api;
  window.F2B.toast=toast;
  window.F2B.esc=esc;
  window.F2B.updatePager=updatePager;
  function normalizeTab(id){
    if(!id) return 'overview';
    if(id==='alerts') return 'overview';
    if(id==='banned-ips' || id==='banned_ips') return 'banned';
    return VALID_TABS[id]?id:'overview';
  }
  function setTabInUrl(id){
    try{
      var url=new URL(location.href);
      url.searchParams.set('tab', id);
      url.hash=id;
      var next=url.pathname+url.search+url.hash;
      if(location.pathname+location.search+location.hash!==next){
        history.replaceState(null,'',next);
      }
    }catch(e){
      try{ history.replaceState(null,'','?tab='+encodeURIComponent(id)+'#'+id); }catch(e2){}
    }
  }
  function tabFromLocation(){
    var params=null;
    try{ params=new URLSearchParams(location.search); }catch(e){}
    var fromQ=params?params.get('tab'):'';
    var fromH=(location.hash||'').replace(/^#/,'').trim();
    var root=document.getElementById('f2bApp');
    var fromData=(root && root.getAttribute('data-active-tab')) || '';
    return normalizeTab(fromQ||fromH||fromData||'overview');
  }
  function switchTab(id, pushUrl){
    id=normalizeTab(id);
    document.querySelectorAll('.f2b-tab').forEach(function(b){b.classList.toggle('active', b.getAttribute('data-tab')===id);});
    document.querySelectorAll('.f2b-panel').forEach(function(p){p.classList.toggle('active', p.id==='panel-'+id);});
    if(pushUrl!==false) setTabInUrl(id);
    if(id==='overview'){ loadOverview(); loadAlerts(); }
    if(id==='jails') loadJails();
    if(id==='banned') loadBanned();
    if(id==='whitelist') loadWhitelist();
    if(id==='blacklist') loadBlacklist();
    if(id==='logs') loadLogs();
    if(id==='statistics') loadStatistics();
    if(id==='settings') loadSettings();
  }
  function updatePager(prefix, page, pages, total){
    var pager=document.getElementById(prefix+'Pager');
    var label=document.getElementById(prefix+'PageLabel');
    var prev=document.getElementById(prefix+'Prev');
    var next=document.getElementById(prefix+'Next');
    var gotoInput=document.getElementById(prefix+'Goto');
    if(!pager) return;
    if(!total){ pager.hidden=true; return; }
    pager.hidden=false;
    if(label) label.textContent='Page '+page+' / '+pages;
    if(prev) prev.disabled=page<=1;
    if(next) next.disabled=page>=pages;
    if(gotoInput){ gotoInput.max=pages; gotoInput.value=page; }
  }
  function loadOverview(){ return window.F2BPanels&&window.F2BPanels.loadOverview?window.F2BPanels.loadOverview():null; }
  function loadAutoban(){ return window.F2BPanels&&window.F2BPanels.loadAutoban?window.F2BPanels.loadAutoban():null; }
  function saveAutoban(extra){ return window.F2BPanels&&window.F2BPanels.saveAutoban?window.F2BPanels.saveAutoban(extra):null; }
  function loadAlerts(){ return window.F2BPanels&&window.F2BPanels.loadAlerts?window.F2BPanels.loadAlerts():null; }
  function loadJails(){ return window.F2BPanels&&window.F2BPanels.loadJails?window.F2BPanels.loadJails():null; }
  async function loadBanned(){
    if(bannedState.loading) return;
    bannedState.loading=true;
    var box=document.getElementById('bannedList');
    var metaEl=document.getElementById('bannedMeta');
    var sizeEl=document.getElementById('bannedPageSize');
    var searchEl=document.getElementById('bannedSearch');
    if(sizeEl) bannedState.pageSize=parseInt(sizeEl.value,10)||50;
    if(searchEl && document.activeElement!==searchEl) searchEl.value=bannedState.q;
    var limit=bannedState.pageSize;
    var page=Math.max(1, bannedState.page|0);
    var offset=(page-1)*limit;
    box.innerHTML='Loading…';
    try{
      var url='/plugins/fail2ban/api/banned-ips/?include_firewall=1&limit='+limit+'&offset='+offset;
      if(bannedState.q) url+='&q='+encodeURIComponent(bannedState.q);
      var data=await api(url);
      if(!data || data.success===false){
        throw new Error((data&&data.error)||'API returned failure');
      }
      var rows=data.data||[];
      var meta=data.meta||{};
      bannedState.total=meta.total!=null?meta.total:rows.length;
      bannedState.pages=meta.pages||Math.max(1, Math.ceil(bannedState.total/limit)||1);
      if(page>bannedState.pages){ bannedState.page=bannedState.pages; bannedState.loading=false; return loadBanned(); }
      if(metaEl){
        var from=bannedState.total? (offset+1) : 0;
        var to=offset+rows.length;
        metaEl.textContent='Showing '+(from? (from+'-'+to) : '0')+' of '+bannedState.total
          +' (fail2ban: '+(meta.fail2ban_count||0)+', firewall: '+(meta.firewall_count||0)+')'
          +(bannedState.q? ' · filter: '+bannedState.q : '')
          +'. Old firewall bans already block; use Import to also add them to the sshd jail.';
      }
      updatePager('banned', bannedState.page, bannedState.pages, bannedState.total);
      if(!rows.length){box.innerHTML='<div class="f2b-empty">No banned IPs'+(bannedState.q?' matching search':'')+'.</div>';return;}
      var html=['<table class="f2b-table"><thead><tr><th>IP</th><th>Source</th><th>Jail / layer</th><th></th></tr></thead><tbody>'];
      for(var i=0;i<rows.length;i++){
        var r=rows[i]||{};
        var ip=r.ip||r.ip_address||'';
        if(typeof r==='string') ip=r;
        var src=r.source||'fail2ban';
        var jail=r.jail||r.jail_name||'-';
        html.push('<tr><td>'+esc(ip)+'</td><td>'+esc(src)+'</td><td>'+esc(jail)+'</td>'
          +'<td><button type="button" class="f2b-btn f2b-btn-soft f2b-btn-sm f2b-manage-banned"'
          +' data-ip="'+esc(ip)+'" data-source="'+esc(src)+'" data-jail="'+esc(jail)+'"'
          +(r.reason?' data-reason="'+esc(r.reason)+'"':'')
          +(r.banned_at?' data-banned-at="'+esc(r.banned_at)+'"':'')
          +'>Manage</button></td></tr>');
      }
      html.push('</tbody></table>');
      box.innerHTML=html.join('');
      box.querySelectorAll('.f2b-manage-banned').forEach(function(btn){
        btn.addEventListener('click', function(){
          if(!window.F2BManage){toast('Manage UI not loaded');return;}
          window.F2BManage.openBanned({
            ip:btn.getAttribute('data-ip'),
            source:btn.getAttribute('data-source'),
            jail:btn.getAttribute('data-jail'),
            reason:btn.getAttribute('data-reason')||'',
            banned_at:btn.getAttribute('data-banned-at')||''
          });
        });
      });
    }catch(e){
      box.innerHTML='<div class="f2b-empty">Failed to load banned IPs'+(e&&e.message?': '+esc(e.message):'')+'.</div>';
      updatePager('banned', 1, 1, 0);
    }finally{
      bannedState.loading=false;
    }
  }
  async function syncFirewallBatch(){
    if(syncRunning){toast('Import already running');return;}
    syncRunning=true;
    var metaEl=document.getElementById('bannedMeta');
    toast('Importing firewall bans into fail2ban (batch)…');
    var offset=0, totalBanned=0, guard=0, lastErr='';
    try{
      while(guard<80){
        guard++;
        var data=await api('/plugins/fail2ban/api/sync-firewall-bans/',{
          method:'POST',
          body:JSON.stringify({jail:'sshd',limit:25,offset:offset})
        });
        if(!data.success){toast(data.error||'Sync failed');break;}
        var d=data.data||{};
        if(d.success===false){toast(d.error||'Sync batch failed');break;}
        totalBanned+=(d.banned||0);
        offset=d.next_offset!=null?d.next_offset:(offset+25);
        var msg='Imported +'+(d.banned||0)+' (run total '+totalBanned+')'
          +(d.candidate_total!=null? ' · ~'+d.candidate_total+' candidates left to walk':'');
        toast(msg);
        if(metaEl) metaEl.textContent=msg+(d.errors&&d.errors.length? ' · errors: '+d.errors.slice(0,3).join('; '):'');
        if(d.errors&&d.errors.length) lastErr=d.errors[0];
        if(d.done || !(d.batch_size>0)) break;
      }
      toast(totalBanned?'Import finished: '+totalBanned+' IP(s) added to sshd'+(lastErr?' (some errors)':''):'Import finished: nothing new to add');
    }catch(e){
      toast('Import failed'+(e&&e.message?': '+e.message:''));
    }finally{
      syncRunning=false;
      bannedState.page=1;
      loadBanned();
      loadOverview();
    }
  }
  function filterWhitelistRows(rows, q){
    q=(q||'').trim().toLowerCase();
    if(!q) return rows.slice();
    return rows.filter(function(r){
      var ip=((r&&r.ip)||r||'').toString().toLowerCase();
      var label=((r&&r.label)||'').toString().toLowerCase();
      var sources=((r&&r.sources)||[]).join(' ').toLowerCase();
      return ip.indexOf(q)!==-1 || label.indexOf(q)!==-1 || sources.indexOf(q)!==-1;
    });
  }
  function renderWhitelistPage(){
    var box=document.getElementById('whitelistList');
    var metaEl=document.getElementById('wlMeta');
    var sizeEl=document.getElementById('wlPageSize');
    if(sizeEl) wlState.pageSize=parseInt(sizeEl.value,10)||50;
    wlState.filtered=filterWhitelistRows(wlState.all, wlState.q);
    var total=wlState.filtered.length;
    var pages=Math.max(1, Math.ceil(total/wlState.pageSize)||1);
    if(wlState.page>pages) wlState.page=pages;
    var offset=(wlState.page-1)*wlState.pageSize;
    var slice=wlState.filtered.slice(offset, offset+wlState.pageSize);
    if(metaEl){
      metaEl.textContent='Showing '+(total?(offset+1)+'-'+(offset+slice.length):'0')+' of '+total
        +' trusted IP(s) (loaded '+(wlState.all.length)+'). Sources: fail2ban ignoreip, Firewall SSH trusted, plugin settings.'
        +(wlState.q?' · filter: '+wlState.q:'');
    }
    updatePager('wl', wlState.page, pages, total);
    if(!slice.length){
      box.innerHTML='<div class="f2b-empty">'+(wlState.all.length?'No whitelist IPs matching search.':'No whitelist IPs yet. Add your office or home public IP so auto-ban and firewall never block you.')+'</div>';
      return;
    }
    box.innerHTML='<table class="f2b-table"><thead><tr><th>IP / CIDR</th><th>Label</th><th>Sources</th><th></th></tr></thead><tbody>'
      +slice.map(function(r){
        var ip=r.ip||r;
        var label=r.label||'';
        var sources=(r.sources||[]).join(', ')||'fail2ban';
        return '<tr><td>'+esc(ip)+'</td><td>'+esc(label)+'</td><td>'+esc(sources)+'</td>'
          +'<td><button type="button" class="f2b-btn f2b-btn-soft f2b-btn-sm f2b-manage-wl" data-ip="'+esc(ip)+'" data-label="'+esc(label)+'" data-sources="'+esc((r.sources||[]).join(','))+'">Manage</button></td></tr>';
      }).join('')+'</tbody></table>';
    box.querySelectorAll('.f2b-manage-wl').forEach(function(btn){
      btn.addEventListener('click', function(){
        if(!window.F2BManage){toast('Manage UI not loaded');return;}
        var srcAttr=btn.getAttribute('data-sources')||'';
        window.F2BManage.openWhitelist({
          ip:btn.getAttribute('data-ip'),
          label:btn.getAttribute('data-label')||'',
          sources:srcAttr?srcAttr.split(',').map(function(s){return s.trim();}).filter(Boolean):[]
        });
      });
    });
  }
  async function loadWhitelist(){
    var box=document.getElementById('whitelistList');
    box.innerHTML='Loading…';
    try{
      var data=await api('/plugins/fail2ban/api/whitelist/');
      wlState.all=data.data||[];
      var meta=data.meta||{};
      if(meta.firewall_synced_into_ignoreip){
        toast(meta.firewall_synced_into_ignoreip);
      }
      var searchEl=document.getElementById('wlSearch');
      if(searchEl && document.activeElement!==searchEl) searchEl.value=wlState.q;
      renderWhitelistPage();
    }catch(e){
      box.innerHTML='<div class="f2b-empty">Failed to load whitelist'+(e&&e.message?': '+esc(e.message):'')+'.</div>';
      updatePager('wl', 1, 1, 0);
    }
  }
  async function addWhitelistOne(){
    var ip=(document.getElementById('wlIp').value||'').trim();
    var label=(document.getElementById('wlLabel').value||'').trim();
    if(!ip){toast('Enter an IP or CIDR');return;}
    var res=await api('/plugins/fail2ban/api/whitelist/',{method:'POST',body:JSON.stringify({ip:ip,label:label,sync_firewall:true})});
    if(res.success){
      toast('Added '+ip+(res.data&&res.data.firewall_synced===false?' (fail2ban only; firewall needs a public IP)':''));
      document.getElementById('wlIp').value='';
      loadWhitelist();
    } else toast(res.error||(res.data&&res.data.error)||'Add failed');
  }
  async function addWhitelistBulk(){
    var text=document.getElementById('wlBulk').value||'';
    if(!text.trim()){toast('Paste one or more IPs first');return;}
    var res=await api('/plugins/fail2ban/api/whitelist/',{method:'POST',body:JSON.stringify({ips_text:text,label:(document.getElementById('wlLabel').value||'').trim(),sync_firewall:true})});
    if(res.success){
      var d=res.data||{};
      toast('Added '+(d.added||[]).length+', skipped '+(d.skipped||[]).length+', errors '+(d.errors||[]).length+' (total '+(d.total||0)+')');
      document.getElementById('wlBulk').value='';
      loadWhitelist();
    } else toast(res.error||(res.data&&res.data.error)||'Bulk import failed');
  }
  async function loadBlacklist(){
    var box=document.getElementById('blacklistList');
    box.innerHTML='Loading…';
    try{
      var data=await api('/plugins/fail2ban/api/blacklist/');
      var rows=data.data||[];
      if(!rows.length){box.innerHTML='<div class="f2b-empty">No blacklisted IPs.</div>';return;}
      box.innerHTML='<table class="f2b-table"><thead><tr><th>IP</th><th></th></tr></thead><tbody>'
        +rows.map(function(ip){
          var v=(typeof ip==='string')?ip:(ip.ip||'');
          return '<tr><td>'+esc(v)+'</td><td><button type="button" class="f2b-btn f2b-btn-soft f2b-btn-sm f2b-manage-bl" data-ip="'+esc(v)+'">Manage</button></td></tr>';
        }).join('')+'</tbody></table>';
      box.querySelectorAll('.f2b-manage-bl').forEach(function(btn){
        btn.addEventListener('click', function(){
          if(!window.F2BManage){toast('Manage UI not loaded');return;}
          window.F2BManage.openBlacklist(btn.getAttribute('data-ip'));
        });
      });
    }catch(e){box.innerHTML='<div class="f2b-empty">Failed to load blacklist.</div>';}
  }
  function loadLogs(){ return window.F2BPanels&&window.F2BPanels.loadLogs?window.F2BPanels.loadLogs():null; }
  function loadStatistics(){ return window.F2BPanels&&window.F2BPanels.loadStatistics?window.F2BPanels.loadStatistics():null; }
  function loadSettings(){ return window.F2BPanels&&window.F2BPanels.loadSettings?window.F2BPanels.loadSettings():null; }
  function wirePager(prefix, onPage){
    var prev=document.getElementById(prefix+'Prev');
    var next=document.getElementById(prefix+'Next');
    var goBtn=document.getElementById(prefix+'GotoBtn');
    var goInput=document.getElementById(prefix+'Goto');
    if(prev) prev.addEventListener('click', function(){ onPage('prev'); });
    if(next) next.addEventListener('click', function(){ onPage('next'); });
    if(goBtn) goBtn.addEventListener('click', function(){ onPage('goto'); });
    if(goInput) goInput.addEventListener('keydown', function(ev){
      if(ev.key==='Enter'){ ev.preventDefault(); onPage('goto'); }
    });
  }

  document.querySelectorAll('.f2b-tab').forEach(function(btn){
    btn.addEventListener('click', function(){ switchTab(btn.getAttribute('data-tab')); });
  });
  window.addEventListener('hashchange', function(){ switchTab(tabFromLocation(), false); });
  window.addEventListener('popstate', function(){ switchTab(tabFromLocation(), false); });
  document.getElementById('autobanEnabled').addEventListener('change', function(){ saveAutoban(); });
  document.getElementById('btnSaveAutoban').addEventListener('click', function(){ saveAutoban(); });
  document.getElementById('btnRunAutoban').addEventListener('click', async function(){
    var data=await api('/plugins/fail2ban/api/autoban/run-now/',{method:'POST',body:'{}'});
    toast(data.success?('Banned '+(data.data&&data.data.banned||0)+' IP(s)'):(data.error||'Run failed'));
    loadAutoban(); loadOverview(); loadAlerts();
  });
  document.getElementById('btnBanAlerts').addEventListener('click', async function(){
    if(!confirm('Permanently ban all current SSH alert IPs?')) return;
    var data=await api('/plugins/fail2ban/api/ban-alert-ips/',{method:'POST',body:JSON.stringify({permanent:true})});
    toast(data.success?('Banned '+(data.data&&data.data.banned||0)+' IP(s)'):(data.error||'Ban failed'));
    loadOverview(); loadBanned();
  });
  document.getElementById('btnRefreshAlerts').addEventListener('click', loadAlerts);
  document.getElementById('btnRefreshBanned').addEventListener('click', function(){ loadBanned(); });
  document.getElementById('btnRefreshWhitelist').addEventListener('click', loadWhitelist);
  document.getElementById('btnRefreshBlacklist').addEventListener('click', loadBlacklist);
  document.getElementById('btnRefreshLogs').addEventListener('click', loadLogs);
  var btnClearLogs=document.getElementById('btnClearLogs');
  if(btnClearLogs) btnClearLogs.addEventListener('click', function(){ window.F2BPanels&&window.F2BPanels.clearLogs&&window.F2BPanels.clearLogs(); });
  document.getElementById('btnRefreshStats').addEventListener('click', loadStatistics);
  document.getElementById('btnAddWhitelist').addEventListener('click', addWhitelistOne);
  document.getElementById('btnBulkWhitelist').addEventListener('click', addWhitelistBulk);
  document.getElementById('btnAddBlacklist').addEventListener('click', async function(){
    var ip=(document.getElementById('blIp').value||'').trim();
    if(!ip){toast('Enter an IP');return;}
    var res=await api('/plugins/fail2ban/api/blacklist/',{method:'POST',body:JSON.stringify({ip:ip})});
    toast(res.success?('Blacklisted '+ip):(res.error||(res.data&&res.data.error)||'Add failed'));
    if(res.success){document.getElementById('blIp').value=''; loadBlacklist();}
  });
  document.getElementById('btnSyncFirewall').addEventListener('click', function(){
    if(!confirm('Import active firewall bans into the sshd jail in batches? Firewall bans already block traffic; this also lists them in fail2ban.')) return;
    syncFirewallBatch();
  });
  document.getElementById('btnRestartF2b').addEventListener('click', async function(){
    var data=await api('/plugins/fail2ban/api/restart/',{method:'POST',body:'{}'});
    toast(data.success?'Fail2ban restarted':(data.error||'Restart failed'));
    loadOverview();
  });
  document.getElementById('btnRestartLs').addEventListener('click', async function(){
    var data=await api('/plugins/fail2ban/api/restart-litespeed/',{method:'POST',body:'{}'});
    toast(data.success?'LiteSpeed restart requested':(data.error||'Restart failed'));
  });
  document.getElementById('settingsForm').addEventListener('submit', async function(e){
    e.preventDefault();
    var body={
      auto_ban_threshold: parseInt(document.getElementById('autoBanThreshold').value,10)||5,
      ban_duration: parseInt(document.getElementById('banDuration').value,10)||3600,
      enabled_jails: document.getElementById('enabledJails').value||'sshd'
    };
    var data=await api('/plugins/fail2ban/api/settings/',{method:'POST',body:JSON.stringify(body)});
    toast(data.success?'Settings saved':(data.error||'Save failed'));
  });
  document.querySelectorAll('[data-tab-jump]').forEach(function(btn){
    btn.addEventListener('click', function(){ switchTab(btn.getAttribute('data-tab-jump')); });
  });
  var btnSyncWl=document.getElementById('btnSyncWlFirewall');
  if(btnSyncWl){
    btnSyncWl.addEventListener('click', async function(){
      try{
        var data=await api('/plugins/fail2ban/api/whitelist/');
        var note=(data.meta&&data.meta.firewall_synced_into_ignoreip)||'Firewall trusted IPs are already in fail2ban ignoreip (or none to add).';
        toast(note);
        loadWhitelist();
      }catch(e){ toast('Whitelist sync failed'+(e&&e.message?': '+e.message:'')); }
    });
  }

  var bannedSearch=document.getElementById('bannedSearch');
  var btnBannedSearch=document.getElementById('btnBannedSearch');
  var bannedPageSize=document.getElementById('bannedPageSize');
  function applyBannedSearch(){
    bannedState.q=(bannedSearch&&bannedSearch.value||'').trim();
    bannedState.page=1;
    loadBanned();
  }
  if(btnBannedSearch) btnBannedSearch.addEventListener('click', applyBannedSearch);
  if(bannedSearch) bannedSearch.addEventListener('keydown', function(ev){
    if(ev.key==='Enter'){ ev.preventDefault(); applyBannedSearch(); }
  });
  if(bannedPageSize) bannedPageSize.addEventListener('change', function(){
    bannedState.pageSize=parseInt(bannedPageSize.value,10)||50;
    bannedState.page=1;
    loadBanned();
  });
  wirePager('banned', function(action){
    if(action==='prev' && bannedState.page>1){ bannedState.page--; loadBanned(); }
    else if(action==='next' && bannedState.page<bannedState.pages){ bannedState.page++; loadBanned(); }
    else if(action==='goto'){
      var n=parseInt((document.getElementById('bannedGoto')||{}).value,10)||1;
      bannedState.page=Math.max(1, Math.min(bannedState.pages||1, n));
      loadBanned();
    }
  });

  var wlSearch=document.getElementById('wlSearch');
  var btnWlSearch=document.getElementById('btnWlSearch');
  var wlPageSize=document.getElementById('wlPageSize');
  function applyWlSearch(){
    wlState.q=(wlSearch&&wlSearch.value||'').trim();
    wlState.page=1;
    renderWhitelistPage();
  }
  if(btnWlSearch) btnWlSearch.addEventListener('click', applyWlSearch);
  if(wlSearch) wlSearch.addEventListener('keydown', function(ev){
    if(ev.key==='Enter'){ ev.preventDefault(); applyWlSearch(); }
  });
  if(wlPageSize) wlPageSize.addEventListener('change', function(){
    wlState.pageSize=parseInt(wlPageSize.value,10)||50;
    wlState.page=1;
    renderWhitelistPage();
  });
  wirePager('wl', function(action){
    var pages=Math.max(1, Math.ceil(wlState.filtered.length/wlState.pageSize)||1);
    if(action==='prev' && wlState.page>1){ wlState.page--; renderWhitelistPage(); }
    else if(action==='next' && wlState.page<pages){ wlState.page++; renderWhitelistPage(); }
    else if(action==='goto'){
      var n=parseInt((document.getElementById('wlGoto')||{}).value,10)||1;
      wlState.page=Math.max(1, Math.min(pages, n));
      renderWhitelistPage();
    }
  });

  var logsPageSize=document.getElementById('logsPageSize');
  if(logsPageSize) logsPageSize.addEventListener('change', function(){
    if(!window.F2BPanels||!window.F2BPanels.logsState) return;
    window.F2BPanels.logsState.pageSize=parseInt(logsPageSize.value,10)||5;
    window.F2BPanels.logsState.page=1;
    if(window.F2BPanels.renderLogsPage) window.F2BPanels.renderLogsPage();
  });
  wirePager('logs', function(action){
    if(!window.F2BPanels||!window.F2BPanels.logsState) return;
    var st=window.F2BPanels.logsState;
    var pages=Math.max(1, Math.ceil(st.all.length/st.pageSize)||1);
    if(action==='prev' && st.page>1){ st.page--; window.F2BPanels.renderLogsPage(); }
    else if(action==='next' && st.page<pages){ st.page++; window.F2BPanels.renderLogsPage(); }
    else if(action==='goto'){
      var n=parseInt((document.getElementById('logsGoto')||{}).value,10)||1;
      st.page=Math.max(1, Math.min(pages, n));
      window.F2BPanels.renderLogsPage();
    }
  });

  window.F2B.loadBanned=loadBanned;
  window.F2B.loadWhitelist=loadWhitelist;
  window.F2B.loadBlacklist=loadBlacklist;
  window.F2B.loadOverview=loadOverview;
  window.F2B.boot=function(){
    loadAutoban();
    switchTab(tabFromLocation(), true);
  };
})();
