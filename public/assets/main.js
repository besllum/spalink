// Navigation (mobil)
const t=document.querySelector('.nav-toggle'),n=document.querySelector('.nav');
if(t){t.addEventListener('click',()=>{const o=n.classList.toggle('open');t.setAttribute('aria-expanded',o)})}

// Diashow Startseite
const hero=document.querySelector('.hero');
if(hero){const imgs=[...hero.querySelectorAll('img')],dots=[...hero.querySelectorAll('.hero-dots button')];let i=0,timer;
 const show=k=>{imgs[i].classList.remove('on');dots[i]?.setAttribute('aria-current','false');i=(k+imgs.length)%imgs.length;imgs[i].classList.add('on');dots[i]?.setAttribute('aria-current','true')};
 const play=()=>{if(!matchMedia('(prefers-reduced-motion: reduce)').matches)timer=setInterval(()=>show(i+1),6000)};
 dots.forEach((d,k)=>d.addEventListener('click',()=>{clearInterval(timer);show(k);play()}));play()}

// Projektfilter
const f=document.querySelector('.filters');
if(f){const btns=[...f.querySelectorAll('button')],cards=[...document.querySelectorAll('.grid .card')];
 const apply=tag=>{btns.forEach(b=>b.setAttribute('aria-pressed',String((b.dataset.tag||'')===tag)));
  cards.forEach(c=>c.hidden=!!tag&&!c.dataset.tags.split('|').includes(tag));
  const u=new URL(location);tag?u.searchParams.set('kategorie',tag):u.searchParams.delete('kategorie');history.replaceState(null,'',u)};
 btns.forEach(b=>b.addEventListener('click',()=>apply(b.dataset.tag||'')));
 apply(new URLSearchParams(location.search).get('kategorie')||'')}

// Bildvergrößerung
const g=document.querySelector('.gallery');
if(g){const items=[...g.querySelectorAll('button')];const d=document.createElement('dialog');d.className='lb';
 d.innerHTML='<figure><img alt=""></figure><button class="x" aria-label="Schließen">×</button><button class="prev" aria-label="Vorheriges Bild">‹</button><button class="next" aria-label="Nächstes Bild">›</button>';
 document.body.append(d);const im=d.querySelector('img');let k=0;
 const open=j=>{k=(j+items.length)%items.length;im.src=items[k].dataset.full;im.alt=items[k].querySelector('img').alt;if(!d.open)d.showModal()};
 items.forEach((b,j)=>b.addEventListener('click',()=>open(j)));
 d.querySelector('.x').onclick=()=>d.close();d.querySelector('.prev').onclick=()=>open(k-1);d.querySelector('.next').onclick=()=>open(k+1);
 d.addEventListener('click',e=>{if(e.target===d||e.target.tagName==='FIGURE')d.close()});
 d.addEventListener('keydown',e=>{if(e.key==='ArrowLeft')open(k-1);if(e.key==='ArrowRight')open(k+1)})}

// Bildgröße im Projektraster (mehr/weniger Projekte pro Zeile)
const sz=document.querySelector('.sizer input'),grid=document.querySelector('.grid.sized');
if(sz&&grid){let v=null;try{v=localStorage.getItem('ss-cols')}catch(e){}
 if(v)sz.value=v;const set=()=>{grid.style.setProperty('--cols',sz.value);try{localStorage.setItem('ss-cols',sz.value)}catch(e){}};
 sz.addEventListener('input',set);set()}
