(function(){
  function api(){ return window.F2B && window.F2B.api; }
  function toast(msg){ if(window.F2B && window.F2B.toast) window.F2B.toast(msg); }
  function esc(s){ return (window.F2B && window.F2B.esc) ? window.F2B.esc(s) : String(s||''); }
  var logsState={page:1,pageSize:5,all:[]};

  async function loadOverview(){
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/status/');
      var d=data.data||{};
      var running=!!d.running;
      document.getElementById('statService').textContent=running?'Active':'Down';
      document.getElementById('f2bServiceChip').textContent='Service: '+(running?'Active':'Down');
      var jails=d.jails||[];
      document.getElementById('statJails').textContent=jails.length||d.total_jails||0;
      var bannedData=await call('/plugins/fail2ban/api/banned-ips/?include_firewall=1&limit=1&offset=0');
      var meta=bannedData.meta||{};
      var total=meta.total!=null?meta.total:((bannedData.data||[]).length||0);
      document.getElementById('statBanned').textContent=total;
      document.getElementById('statBanned').parentNode.querySelector('.hint').textContent=
        'fail2ban '+(meta.fail2ban_count||0)+' + firewall '+(meta.firewall_count||0);
    }catch(e){toast('Could not load status');}
  }
  async function loadAutoban(){
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/autoban/');
      var c=data.data||{};
      document.getElementById('autobanEnabled').checked=!!c.enabled;
      document.getElementById('autobanInterval').value=c.check_interval||60;
      document.getElementById('autobanJail').value=c.jail||'sshd';
      document.getElementById('autobanPermanent').value=c.permanent?'1':'0';
      document.getElementById('statAutoban').textContent=c.enabled?'On':'Off';
      var line='Auto-ban is '+(c.enabled?'enabled':'disabled')+'.';
      if(c.last_run_at) line+=' Last run: '+c.last_run_at+'. Banned last pass: '+(c.last_banned_count||0)+'.';
      if(c.last_error) line+=' Last error: '+c.last_error;
      document.getElementById('autobanStatus').textContent=line;
    }catch(e){document.getElementById('autobanStatus').textContent='Could not load auto-ban config'+(e&&e.message?': '+e.message:'');}
  }
  async function saveAutoban(extra){
    var call=api(); if(!call) return;
    var body=Object.assign({
      enabled: document.getElementById('autobanEnabled').checked,
      check_interval: parseInt(document.getElementById('autobanInterval').value,10)||60,
      jail: document.getElementById('autobanJail').value||'sshd',
      permanent: document.getElementById('autobanPermanent').value==='1'
    }, extra||{});
    var data=await call('/plugins/fail2ban/api/autoban/',{method:'POST',body:JSON.stringify(body)});
    if(data.success){
      toast(body.enabled?'Auto-ban enabled':'Auto-ban saved');
      if(data.data && typeof data.data.just_banned==='number') toast('Auto-ban pass banned '+data.data.just_banned+' IP(s)');
      loadAutoban(); loadOverview();
    } else toast(data.error||'Save failed');
  }
  async function loadAlerts(){
    var box=document.getElementById('alertsList');
    box.innerHTML='Loading…';
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/ssh-alerts/');
      var alerts=(data.data&&data.data.alerts)||[];
      window._f2bAlertIps=(data.data&&data.data.ips)||[];
      if(!alerts.length){box.innerHTML='<div class="f2b-empty">No SSH security threats in recent logs.</div>';return;}
      box.innerHTML=alerts.map(function(a){
        return '<div class="f2b-alert"><h4>'+esc(a.title)+' · '+esc(a.severity)+'</h4><p>'+esc(a.description)+'</p>'
          +((a.ips&&a.ips.length)?'<p style="margin-top:6px"><strong>IPs:</strong> '+esc(a.ips.join(', '))+'</p>':'')+'</div>';
      }).join('')+'<div class="f2b-statusline">Unique alert IPs: <strong>'+window._f2bAlertIps.length+'</strong></div>';
    }catch(e){box.innerHTML='<div class="f2b-empty">Failed to load alerts.</div>';}
  }
  async function loadJails(){
    var box=document.getElementById('jailsList');
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/jails/');
      var jails=data.data||[];
      if(!jails.length){box.innerHTML='<div class="f2b-empty">No jails found.</div>';return;}
      box.innerHTML='<table class="f2b-table"><thead><tr><th>Jail</th><th>Status</th><th>Banned</th></tr></thead><tbody>'
        +jails.map(function(j){
          var name=j.name||j.jail||j;
          var banned=j.currently_banned!=null?j.currently_banned:(j.banned||'-');
          var st=j.status||(j.enabled===false?'disabled':'active');
          return '<tr><td>'+esc(name)+'</td><td>'+esc(st)+'</td><td>'+esc(banned)+'</td></tr>';
        }).join('')+'</tbody></table>';
    }catch(e){box.innerHTML='<div class="f2b-empty">Failed to load jails.</div>';}
  }
  function parseLogLine(line){
    var raw=String(line||'');
    var m=raw.match(/^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:,\d+)?)\s+(\S+)\s+(?:\[\d+\]:\s*)?([A-Z]+)\s+(.*)$/);
    if(m){
      return {ts:m[1], src:m[2], level:m[3], msg:m[4], raw:raw};
    }
    // journalctl-style: "Aug 04 21:22:37 host systemd[1]: ..."
    var j=raw.match(/^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+(\S+):\s*(.*)$/);
    if(j){
      return {ts:j[1], src:j[2], level:'', msg:j[3], raw:raw};
    }
    return {ts:'', src:'', level:'', msg:raw, raw:raw};
  }
  function levelClass(level){
    var l=String(level||'').toUpperCase();
    if(l==='ERROR'||l==='CRITICAL'||l==='FATAL') return 'is-error';
    if(l==='WARN'||l==='WARNING') return 'is-warn';
    if(l==='INFO'||l==='NOTICE'||l==='DEBUG') return 'is-info';
    return '';
  }
  async function loadLogs(){
    var box=document.getElementById('logsList');
    var metaEl=document.getElementById('logsMeta');
    var sizeEl=document.getElementById('logsPageSize');
    if(sizeEl) logsState.pageSize=parseInt(sizeEl.value,10)||5;
    box.className='f2b-log-viewer f2b-empty';
    box.textContent='Loading…';
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/logs/?lines=500');
      var lines=data.data||[];
      // File order is oldest→newest; reverse so page 1 is newest.
      logsState.all=lines.slice().reverse();
      logsState.page=1;
      renderLogsPage();
    }catch(e){
      logsState.all=[];
      if(metaEl) metaEl.textContent='';
      box.className='f2b-log-viewer f2b-empty';
      box.textContent='Failed to load logs'+(e&&e.message?': '+e.message:'');
      var pager=document.getElementById('logsPager');
      if(pager) pager.hidden=true;
    }
  }
  function renderLogsPage(){
    var box=document.getElementById('logsList');
    var metaEl=document.getElementById('logsMeta');
    var sizeEl=document.getElementById('logsPageSize');
    if(sizeEl) logsState.pageSize=parseInt(sizeEl.value,10)||5;
    var total=logsState.all.length;
    var pages=Math.max(1, Math.ceil(total/logsState.pageSize)||1);
    if(logsState.page>pages) logsState.page=pages;
    if(logsState.page<1) logsState.page=1;
    var offset=(logsState.page-1)*logsState.pageSize;
    var slice=logsState.all.slice(offset, offset+logsState.pageSize);
    if(!total){
      box.className='f2b-log-viewer f2b-empty';
      box.textContent='No recent fail2ban log lines.';
      if(metaEl) metaEl.textContent='No lines in the last 500 from fail2ban.log.';
    }else{
      box.className='f2b-log-viewer';
      box.innerHTML=slice.map(function(line){
        var p=parseLogLine(line);
        var lc=levelClass(p.level);
        var metaBits='';
        if(p.ts) metaBits+='<span class="f2b-log-ts">'+esc(p.ts)+'</span>';
        if(p.level) metaBits+='<span class="f2b-log-level '+(lc||'')+'">'+esc(p.level)+'</span>';
        if(p.src) metaBits+='<span class="f2b-log-src">'+esc(p.src)+'</span>';
        if(!metaBits){
          return '<article class="f2b-log-line"><p class="f2b-log-msg">'+esc(p.msg)+'</p></article>';
        }
        return '<article class="f2b-log-line">'
          +'<div class="f2b-log-meta">'+metaBits+'</div>'
          +'<p class="f2b-log-msg">'+esc(p.msg)+'</p>'
          +'</article>';
      }).join('');
      var from=offset+1;
      var to=offset+slice.length;
      if(metaEl){
        metaEl.textContent='Showing '+from+'-'+to+' of '+total+' (newest first). Fetched last 500 from fail2ban.log.';
      }
    }
    if(window.F2B&&window.F2B.updatePager){
      window.F2B.updatePager('logs', logsState.page, pages, total);
    }else{
      var pager=document.getElementById('logsPager');
      var label=document.getElementById('logsPageLabel');
      var prev=document.getElementById('logsPrev');
      var next=document.getElementById('logsNext');
      var gotoInput=document.getElementById('logsGoto');
      if(pager){
        if(!total){ pager.hidden=true; }
        else{
          pager.hidden=false;
          if(label) label.textContent='Page '+logsState.page+' / '+pages;
          if(prev) prev.disabled=logsState.page<=1;
          if(next) next.disabled=logsState.page>=pages;
          if(gotoInput){ gotoInput.max=pages; gotoInput.value=logsState.page; }
        }
      }
    }
  }
  async function clearLogs(){
    if(!window.confirm('Clear /var/log/fail2ban.log?\n\nThis permanently empties the active fail2ban log file. Rotated archives are not deleted.')){
      return;
    }
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/logs/clear/',{method:'POST',body:'{}'});
      if(!data||data.success===false){
        throw new Error((data&&data.error)||'Clear failed');
      }
      toast(data.message||'Log cleared');
      await loadLogs();
    }catch(e){
      toast('Could not clear log'+(e&&e.message?': '+e.message:''));
    }
  }
  async function loadStatistics(){
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/statistics/');
      var s=data.data||{};
      document.getElementById('statEvents').textContent=s.total_events!=null?s.total_events:'-';
      document.getElementById('statStatsBanned').textContent=s.banned_ips!=null?s.banned_ips:'-';
      document.getElementById('statUnbanned').textContent=s.unbanned_ips!=null?s.unbanned_ips:'-';
      document.getElementById('statCurrentBanned').textContent=s.currently_banned!=null?s.currently_banned:'-';
      var by=s.events_by_type||{};
      document.getElementById('statsExtra').textContent=
        'Live bans: fail2ban '+(s.fail2ban_banned||0)+' + firewall '+(s.firewall_banned||0)
        +'. Last 30d by type: ban '+(by.ban||0)+', unban '+(by.unban||0)+', attack '+(by.attack||0)
        +', whitelist '+(by.whitelist||0)+', blacklist '+(by.blacklist||0)+'.';
    }catch(e){
      document.getElementById('statsExtra').textContent='Failed to load statistics'+(e&&e.message?': '+e.message:'');
    }
  }
  async function loadSettings(){
    try{
      var call=api(); if(!call) return;
      var data=await call('/plugins/fail2ban/api/settings/');
      var s=data.data||{};
      document.getElementById('autoBanThreshold').value=s.auto_ban_threshold||5;
      document.getElementById('banDuration').value=s.ban_duration||3600;
      document.getElementById('enabledJails').value=s.enabled_jails||'sshd';
    }catch(e){
      toast('Could not load settings'+(e&&e.message?': '+e.message:''));
    }
  }

  window.F2BPanels={
    loadOverview:loadOverview,
    loadAutoban:loadAutoban,
    saveAutoban:saveAutoban,
    loadAlerts:loadAlerts,
    loadJails:loadJails,
    loadLogs:loadLogs,
    clearLogs:clearLogs,
    renderLogsPage:renderLogsPage,
    logsState:logsState,
    loadStatistics:loadStatistics,
    loadSettings:loadSettings
  };
})();
