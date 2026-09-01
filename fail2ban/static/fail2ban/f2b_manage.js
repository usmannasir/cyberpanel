(function(){
  var modal=document.getElementById('f2bManageModal');
  if(!modal) return;
  var titleEl=document.getElementById('f2bManageTitle');
  var bodyEl=document.getElementById('f2bManageBody');
  var actionsEl=document.getElementById('f2bManageActions');
  var statusEl=document.getElementById('f2bManageStatus');
  var current=null;
  var busy=false;

  function api(){ return (window.F2B && window.F2B.api) ? window.F2B.api : null; }
  function toast(msg){ if(window.F2B && window.F2B.toast) window.F2B.toast(msg); }
  function esc(s){ return (window.F2B && window.F2B.esc) ? window.F2B.esc(s) : String(s||''); }
  function reload(kind){
    if(!window.F2B) return;
    if(kind==='banned' && window.F2B.loadBanned) window.F2B.loadBanned();
    if(kind==='whitelist' && window.F2B.loadWhitelist) window.F2B.loadWhitelist();
    if(kind==='blacklist' && window.F2B.loadBlacklist) window.F2B.loadBlacklist();
    if(window.F2B.loadOverview) window.F2B.loadOverview();
  }
  function setStatus(msg, isErr){
    if(!statusEl) return;
    statusEl.textContent=msg||'';
    statusEl.style.color=isErr?'#dc2626':'';
  }
  function closeModal(){
    modal.hidden=true;
    current=null;
    busy=false;
    setStatus('');
  }
  function openModal(){
    modal.hidden=false;
    try{ document.getElementById('f2bManageClose').focus(); }catch(e){}
  }
  function btn(label, cls, action){
    return '<button type="button" class="f2b-btn '+cls+'" data-f2b-act="'+esc(action)+'">'+esc(label)+'</button>';
  }
  function copyText(text){
    text=String(text||'');
    if(!text) return;
    if(navigator.clipboard && navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(function(){ toast('Copied '+text); }).catch(function(){
        window.prompt('Copy IP', text);
      });
    } else {
      window.prompt('Copy IP', text);
    }
  }
  async function run(action){
    if(busy || !current) return;
    var call=api();
    if(!call){ setStatus('API helper not ready', true); return; }
    busy=true;
    setStatus('Working…');
    try{
      var kind=current.kind;
      var ip=current.ip;
      var res;
      if(kind==='banned'){
        if(action==='copy'){ copyText(ip); setStatus(''); busy=false; return; }
        if(action==='unban_jail'){
          res=await call('/plugins/fail2ban/api/unban-ip/',{method:'POST',body:JSON.stringify({ip:ip,jail:current.jail||'sshd',layers:'fail2ban'})});
        } else if(action==='unban_fw'){
          res=await call('/plugins/fail2ban/api/unban-ip/',{method:'POST',body:JSON.stringify({ip:ip,layers:'firewall',source:'firewall'})});
        } else if(action==='unban_both'){
          res=await call('/plugins/fail2ban/api/unban-ip/',{method:'POST',body:JSON.stringify({ip:ip,jail:current.jail||'sshd',layers:'both'})});
        } else if(action==='whitelist'){
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'POST',body:JSON.stringify({ip:ip,label:'Unbanned via Manage',sync_firewall:true})});
          if(res && res.success){
            await call('/plugins/fail2ban/api/unban-ip/',{method:'POST',body:JSON.stringify({ip:ip,jail:current.jail||'sshd',layers:'both'})});
          }
        } else if(action==='blacklist'){
          res=await call('/plugins/fail2ban/api/blacklist/',{method:'POST',body:JSON.stringify({ip:ip})});
        }
      } else if(kind==='whitelist'){
        if(action==='copy'){ copyText(ip); setStatus(''); busy=false; return; }
        if(action==='save_label'){
          var labelInput=document.getElementById('f2bManageLabel');
          var label=(labelInput && labelInput.value || '').trim();
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'POST',body:JSON.stringify({ip:ip,label:label,sync_firewall:true})});
        } else if(action==='ensure_both'){
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'POST',body:JSON.stringify({ip:ip,label:current.label||'',sync_firewall:true})});
        } else if(action==='remove_f2b'){
          if(!confirm('Remove '+ip+' from fail2ban ignoreip only?')){ busy=false; setStatus(''); return; }
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'DELETE',body:JSON.stringify({ip:ip,layers:'fail2ban'})});
        } else if(action==='remove_fw'){
          if(!confirm('Remove '+ip+' from Firewall SSH trusted only?')){ busy=false; setStatus(''); return; }
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'DELETE',body:JSON.stringify({ip:ip,layers:'firewall'})});
        } else if(action==='remove_both'){
          if(!confirm('Remove '+ip+' from fail2ban and Firewall trusted?')){ busy=false; setStatus(''); return; }
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'DELETE',body:JSON.stringify({ip:ip,layers:'both'})});
        } else if(action==='to_blacklist'){
          if(!confirm('Move '+ip+' to blacklist (remove whitelist + add firewall drop)?')){ busy=false; setStatus(''); return; }
          await call('/plugins/fail2ban/api/whitelist/',{method:'DELETE',body:JSON.stringify({ip:ip,layers:'both'})});
          res=await call('/plugins/fail2ban/api/blacklist/',{method:'POST',body:JSON.stringify({ip:ip})});
          kind='blacklist';
        }
      } else if(kind==='blacklist'){
        if(action==='copy'){ copyText(ip); setStatus(''); busy=false; return; }
        if(action==='remove'){
          if(!confirm('Remove '+ip+' from blacklist?')){ busy=false; setStatus(''); return; }
          res=await call('/plugins/fail2ban/api/blacklist/',{method:'DELETE',body:JSON.stringify({ip:ip})});
        } else if(action==='ban_jail'){
          res=await call('/plugins/fail2ban/api/ban-ip/',{method:'POST',body:JSON.stringify({ip:ip,jail:'sshd',permanent:false})});
        } else if(action==='to_whitelist'){
          if(!confirm('Move '+ip+' to whitelist (remove blacklist + trust IP)?')){ busy=false; setStatus(''); return; }
          await call('/plugins/fail2ban/api/blacklist/',{method:'DELETE',body:JSON.stringify({ip:ip})});
          res=await call('/plugins/fail2ban/api/whitelist/',{method:'POST',body:JSON.stringify({ip:ip,label:'Moved from blacklist',sync_firewall:true})});
          kind='whitelist';
        }
      }
      if(action==='copy'){ busy=false; return; }
      if(!res || res.success===false){
        throw new Error((res && (res.error||res.error_message)) || 'Action failed');
      }
      toast(res.data && res.data.message ? res.data.message : 'Done');
      setStatus('Done.');
      reload(current.kind);
      if(kind!==current.kind) reload(kind);
      closeModal();
    }catch(e){
      setStatus((e && e.message) || 'Action failed', true);
      toast((e && e.message) || 'Action failed');
    }finally{
      busy=false;
    }
  }

  function renderBanned(row){
    current={kind:'banned', ip:row.ip, source:row.source||'fail2ban', jail:row.jail||'sshd', reason:row.reason||'', banned_at:row.banned_at||''};
    titleEl.textContent='Manage banned IP';
    bodyEl.innerHTML='<dl class="f2b-modal-dl">'
      +'<dt>IP</dt><dd><code>'+esc(current.ip)+'</code></dd>'
      +'<dt>Source</dt><dd>'+esc(current.source)+'</dd>'
      +'<dt>Jail / layer</dt><dd>'+esc(current.jail)+'</dd>'
      +(current.reason?'<dt>Reason</dt><dd>'+esc(current.reason)+'</dd>':'')
      +(current.banned_at?'<dt>Banned at</dt><dd>'+esc(current.banned_at)+'</dd>':'')
      +'</dl><p class="f2b-statusline" style="margin:0">Unban from one layer or both. Whitelist also unbans so the IP is never re-blocked by auto-ban.</p>';
    var acts=[];
    acts.push(btn('Copy IP','f2b-btn-soft','copy'));
    if(current.source!=='firewall'){
      acts.push(btn('Unban fail2ban','f2b-btn-ok','unban_jail'));
    }
    acts.push(btn('Unban firewall','f2b-btn-soft','unban_fw'));
    acts.push(btn('Unban both','f2b-btn-ok','unban_both'));
    acts.push(btn('Unban + whitelist','f2b-btn-soft','whitelist'));
    acts.push(btn('Add to blacklist','f2b-btn-danger','blacklist'));
    actionsEl.innerHTML=acts.join('');
    openModal();
  }

  function renderWhitelist(row){
    current={kind:'whitelist', ip:row.ip, label:row.label||'', sources:(row.sources||[]).slice()};
    titleEl.textContent='Manage whitelist IP';
    bodyEl.innerHTML='<dl class="f2b-modal-dl">'
      +'<dt>IP / CIDR</dt><dd><code>'+esc(current.ip)+'</code></dd>'
      +'<dt>Sources</dt><dd>'+esc((current.sources||[]).join(', ')||'—')+'</dd>'
      +'</dl>'
      +'<div class="f2b-field"><label for="f2bManageLabel">Label</label>'
      +'<input type="text" id="f2bManageLabel" value="'+esc(current.label)+'" placeholder="e.g. Office / Home PC" autocomplete="off"></div>';
    actionsEl.innerHTML=[
      btn('Copy IP','f2b-btn-soft','copy'),
      btn('Save label','f2b-btn-ok','save_label'),
      btn('Ensure fail2ban + firewall','f2b-btn-soft','ensure_both'),
      btn('Remove fail2ban only','f2b-btn-soft','remove_f2b'),
      btn('Remove firewall only','f2b-btn-soft','remove_fw'),
      btn('Remove both','f2b-btn-danger','remove_both'),
      btn('Move to blacklist','f2b-btn-danger','to_blacklist')
    ].join('');
    openModal();
  }

  function renderBlacklist(ip){
    current={kind:'blacklist', ip:ip};
    titleEl.textContent='Manage blacklist IP';
    bodyEl.innerHTML='<dl class="f2b-modal-dl">'
      +'<dt>IP</dt><dd><code>'+esc(current.ip)+'</code></dd>'
      +'<dt>Layer</dt><dd>Firewall permanent drop</dd>'
      +'</dl>';
    actionsEl.innerHTML=[
      btn('Copy IP','f2b-btn-soft','copy'),
      btn('Also ban in fail2ban','f2b-btn-soft','ban_jail'),
      btn('Move to whitelist','f2b-btn-ok','to_whitelist'),
      btn('Remove from blacklist','f2b-btn-danger','remove')
    ].join('');
    openModal();
  }

  document.getElementById('f2bManageClose').addEventListener('click', closeModal);
  modal.addEventListener('click', function(ev){
    if(ev.target && ev.target.getAttribute('data-f2b-modal-close')) closeModal();
  });
  document.addEventListener('keydown', function(ev){
    if(ev.key==='Escape' && !modal.hidden) closeModal();
  });
  actionsEl.addEventListener('click', function(ev){
    var btnEl=ev.target.closest('[data-f2b-act]');
    if(!btnEl) return;
    run(btnEl.getAttribute('data-f2b-act'));
  });

  window.F2BManage={
    openBanned: renderBanned,
    openWhitelist: renderWhitelist,
    openBlacklist: function(ip){ renderBlacklist(typeof ip==='string'?ip:(ip&&ip.ip)||''); },
    close: closeModal
  };
})();
