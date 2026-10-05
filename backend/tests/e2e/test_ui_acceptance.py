"""Measured UI checks; these do not replace a complete WCAG or human usability audit."""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from test_dashboard import live_server
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import (
    AssetRecord, BuildingRecord, FloorRecord, OrganizationRecord, RoomRecord,
)
from assetguard.modules.identity.auth import hash_password
from assetguard.modules.identity.models import LocationAccessRecord, UserRecord

pytestmark = pytest.mark.skipif(os.environ.get('ASSETGUARD_RUN_BROWSER_E2E') != '1', reason='Browser checks are opt-in.')


def seed_school(session, name, count):
    now = datetime.now(UTC)
    organization = OrganizationRecord(name=name, created_at=now)
    session.add(organization)
    session.flush()
    building = BuildingRecord(organization_id=organization.id, name='Корпус', created_at=now)
    session.add(building)
    session.flush()
    floor = FloorRecord(building_id=building.id, name='1', created_at=now)
    session.add(floor)
    session.flush()
    room = RoomRecord(floor_id=floor.id, name='101', created_at=now)
    session.add(room)
    session.flush()
    assets = [
        AssetRecord(
            organization_id=organization.id, room_id=room.id,
            inventory_number=f'{name}-{index:06d}', name=f'Стол {index:06d}',
            asset_type='Furniture', category='FURNITURE', tracking_mode='GROUPED',
            quantity=12, unit='шт.', status='ACTIVE', building='Корпус', floor='1', room='101',
            created_at=now, updated_at=now,
        )
        for index in range(count)
    ]
    session.add_all(assets)
    session.flush()
    return (organization, room, assets)
PERFORMANCE_OBSERVER = r"""(() => {
  window.uiMetrics={lcp:0,cls:0,events:[],longTasks:[]};
  for(const type of ['largest-contentful-paint','layout-shift','event','longtask']){
    if(!PerformanceObserver.supportedEntryTypes.includes(type))continue;
    new PerformanceObserver(list=>{
      for(const entry of list.getEntries()){
        if(type==='largest-contentful-paint')uiMetrics.lcp=entry.startTime;
        if(type==='layout-shift'&&!entry.hadRecentInput)uiMetrics.cls+=entry.value;
        if(type==='event'&&entry.interactionId)uiMetrics.events.push({name:entry.name,duration:entry.duration,interactionId:entry.interactionId});
        if(type==='longtask')uiMetrics.longTasks.push(entry.duration);
      }
    }).observe(type==='event'?{type,buffered:true,durationThreshold:16}:{type,buffered:true});
  }
})()"""


@pytest.mark.parametrize('count', [216, 1000])
def test_registry_capacity_retains_filters_and_limits_rendering(live_server, count):
    playwright = pytest.importorskip('playwright.sync_api')
    with get_session_factory()() as session:
        seed_school(session, 'Capacity', count)
        session.commit()
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        context = browser.new_context(viewport={'width': 1366, 'height': 900}, reduced_motion='reduce')
        page = context.new_page()
        page.set_default_timeout(15000)
        page.add_init_script(PERFORMANCE_OBSERVER)
        page.goto(live_server + '/#devices')
        page.locator('#login-mode').click()
        page.locator('#token').fill(os.environ['ASSETGUARD_ADMIN_SHARED_SECRET'])
        started = page.evaluate('performance.now()')
        page.locator('#login').click()
        page.locator('#status').filter(has_text='Данные актуальны').wait_for()
        cold = page.evaluate('performance.now()') - started
        assert page.locator('#assets tr').count() == 20
        for _ in range(3):
            page.locator('#device-pagination').get_by_role('button', name='Следующая').click()
        assert page.locator('#assets tr').count() == 20
        page.locator('#device-search').fill('Capacity-000009')
        assert page.locator('#assets tr').count() == 1
        link = page.locator('#assets .device-open-link').first
        link.focus()
        page.keyboard.press('Enter')
        page.locator('#detail').wait_for(state='visible')
        page.locator('#detail-back').focus()
        page.keyboard.press('Enter')
        page.locator('#devices').wait_for(state='visible')
        assert page.locator('#device-search').input_value() == 'Capacity-000009'
        assert page.locator('#assets tr').count() == 1
        page.locator('#device-search').fill('')
        started = page.evaluate('performance.now()')
        page.locator('#refresh-data').click()
        page.locator('#status').filter(has_text='Данные актуальны').wait_for()
        page.wait_for_function("document.querySelector('#app-main').dataset.loadState==='ready'")
        warm = page.evaluate('performance.now()') - started
        reports = page.evaluate('uiMetrics')
        reports.update({
            'assets': count, 'cold_workspace_ms': cold, 'warm_workspace_ms': warm,
            'rendered_rows': page.locator('#assets tr').count(), 'browser': browser.version,
            'viewport': {'width': 1366, 'height': 900}, 'network': 'localhost, no throttling',
            'cpu_throttling': False, 'lcp_scope': 'document/login; not authenticated workspace',
        })
        output = os.environ.get('ASSETGUARD_UI_PERFORMANCE_DIR')
        if output:
            path = Path(output)
            path.mkdir(parents=True, exist_ok=True)
            (path / f'capacity-{count}.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
        assert reports['rendered_rows'] == 20
        assert not page.evaluate(MEASURE_CONTRAST)['issues']
        print('UI capacity:', json.dumps(reports))
        context.close()
        browser.close()


@pytest.mark.parametrize('role', ['ADMIN', 'VIEWER', 'LOCATION_MANAGER', 'INVENTORY_CLERK'])
def test_named_role_keyboard_workflow_keeps_tenant_boundary(live_server, role):
    playwright = pytest.importorskip('playwright.sync_api')
    with get_session_factory()() as session:
        own, room, _ = seed_school(session, 'Own', 1)
        _, foreign_room, foreign_assets = seed_school(session, 'Foreign', 1)
        user = UserRecord(
            username='role-test', password_hash=hash_password('test-password'), role=role,
            organization_id=own.id, is_active=True, created_at=datetime.now(UTC),
        )
        session.add(user)
        session.flush()
        if role != 'ADMIN':
            session.add(LocationAccessRecord(
                user_id=user.id, scope_type='ROOM', scope_id=room.id,
                permission='VIEWER' if role == 'VIEWER' else 'EDITOR', created_at=datetime.now(UTC),
            ))
        session.commit()
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={'width': 390, 'height': 900}, reduced_motion='reduce')
        page.set_default_timeout(10000)
        page.goto(live_server + '/#devices')
        page.locator('#username').fill('role-test')
        page.locator('#token').fill('test-password')
        page.locator('#token').focus()
        page.keyboard.press('Enter')
        page.locator('#status').filter(has_text='Данные актуальны').wait_for()
        assert page.locator('#assets tr').count() == 1
        assert 'Foreign' not in page.locator('#assets').inner_text()
        assert page.locator('#show-create').is_visible() == (role != 'VIEWER')
        link = page.locator('#assets .device-open-link').first
        link.focus()
        page.keyboard.press('Enter')
        page.locator('#detail').wait_for(state='visible')
        token = page.evaluate("sessionStorage.getItem('assetguard-admin-token')")
        headers = {'X-AssetGuard-Admin-Token': token}
        assert page.request.get(live_server + f'/admin/assets/{foreign_assets[0].id}', headers=headers).status == 404
        assert page.request.get(live_server + f'/admin/locations/rooms/{foreign_room.id}/workspace', headers=headers).status == 404
        assert page.request.get(live_server + '/admin/notifications', headers=headers).status == (200 if role == 'ADMIN' else 401)
        page.locator('#detail-back').focus()
        page.keyboard.press('Enter')
        page.locator('#devices').wait_for(state='visible')
        assert not page.evaluate(MEASURE_CONTRAST)['issues']
        page.locator('#logout').focus()
        page.keyboard.press('Enter')
        page.locator('#auth-screen').wait_for(state='visible')
        assert not page.evaluate("sessionStorage.getItem('assetguard-admin-token')")
        browser.close()
MEASURE_CONTRAST = r"""() => {
  const rgba = value => {const parts=value.match(/[\d.]+/g).map(Number);return [...parts.slice(0,3),parts[3]??1];};
  const blend = (fg,bg) => fg.slice(0,3).map((channel,index)=>channel*fg[3]+bg[index]*(1-fg[3]));
  const background = element => {
    const chain=[];for(let node=element;node;node=node.parentElement)chain.unshift(node);
    let color=[255,255,255];for(const node of chain)color=blend(rgba(getComputedStyle(node).backgroundColor),color);
    return color;
  };
  const luminance = color => color.map(channel=>{const value=channel/255;return value<=.04045?value/12.92:((value+.055)/1.055)**2.4;}).reduce((sum,value,index)=>sum+value*[.2126,.7152,.0722][index],0);
  const ratio = (a,b) => {const values=[luminance(a),luminance(b)].sort((a,b)=>b-a);return (values[0]+.05)/(values[1]+.05);};
  const visible = node => node.getClientRects().length && getComputedStyle(node).visibility!=="hidden" && !node.closest('[disabled],.sr-only');
  const issues=[], samples=[], borders=[];
  const checked=new Set();
  for(const element of document.querySelectorAll('body *')){
    if(!visible(element)||['SCRIPT','STYLE','OPTION','SVG','PATH'].includes(element.tagName))continue;
    const text=[...element.childNodes].some(node=>node.nodeType===Node.TEXT_NODE&&node.textContent.trim());
    const input=['INPUT','SELECT','TEXTAREA'].includes(element.tagName);
    if(!text&&!input)continue;
    const style=getComputedStyle(element), bg=background(element),fg=blend(rgba(style.color),bg);
    const measured=ratio(fg,bg),large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.6667&&parseInt(style.fontWeight)>=700);
    const key=[style.color,bg.join(','),large].join('|');
    if(!checked.has(key)){
      checked.add(key);const sample={id:element.id||element.className||element.tagName,ratio:measured,minimum:large?3:4.5,color:style.color,background:bg};
      samples.push(sample);if(measured<sample.minimum)issues.push(sample);
    }
    if(input&&!['checkbox','radio','hidden','file'].includes(element.type)){
      const measured=ratio(blend(rgba(style.borderTopColor),bg),bg);
      borders.push({id:element.id||element.name,ratio:measured});
    }
  }
  return {issues,samples,borders};
}"""


def focus_snapshot(page):
    return page.evaluate(r"""() => {
      const element=document.activeElement,style=getComputedStyle(element),rect=element.getBoundingClientRect();
      const x=Math.max(0,Math.min(innerWidth-1,rect.x+rect.width/2)),y=Math.max(0,Math.min(innerHeight-1,rect.y+rect.height/2));
      const top=document.elementFromPoint(x,y);
      return {id:element.id||element.textContent.slice(0,45),outline:parseFloat(style.outlineWidth),
              keyboard:element.matches(':focus-visible'),visible:rect.bottom>0&&rect.top<innerHeight&&rect.right>0&&rect.left<innerWidth,
              uncovered:!!top&&(top===element||element.contains(top)),inDialog:!!element.closest('dialog[open]')};
    }""")


def test_workspace_contrast_names_reflow_and_keyboard(live_server):
    playwright = pytest.importorskip('playwright.sync_api')
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={'width': 1366, 'height': 900}, reduced_motion='reduce')
        page.set_default_timeout(10000)
        page.goto(live_server)
        reports = {'login': page.evaluate(MEASURE_CONTRAST)}
        page.locator('#login-mode').click()
        page.locator('#token').fill(os.environ['ASSETGUARD_ADMIN_SHARED_SECRET'])
        page.locator('#login').click()
        page.locator('#status').filter(has_text='Данные актуальны').wait_for()
        for route in ('overview', 'devices', 'incidents', 'locations', 'data-exchange', 'agent-credentials', 'location-access'):
            page.evaluate('route=>location.hash=route', route)
            page.locator(f'#{route}').wait_for(state='visible')
            reports[route] = page.evaluate(MEASURE_CONTRAST)
            unnamed = page.locator('input:visible,select:visible,textarea:visible').evaluate_all("elements=>elements.filter(element=>!element.labels?.length&&!element.getAttribute('aria-label')&&!element.getAttribute('aria-labelledby')).map(element=>element.id||element.name)")
            assert not unnamed, {'route': route, 'unnamed': unnamed}
            for width, height in ((1920, 900), (1366, 900), (1024, 900), (768, 900), (390, 900), (360, 900), (320, 900), (640, 400), (320, 256)):
                page.set_viewport_size({'width': width, 'height': height})
                assert page.locator('body').evaluate('element=>element.scrollWidth<=element.clientWidth'), {'route': route, 'width': width, 'height': height}
            page.set_viewport_size({'width': 1366, 'height': 900})
        output = os.environ.get('ASSETGUARD_UI_MEASUREMENT_REPORT')
        if output:
            Path(output).write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
        failures = {name: report['issues'] for name, report in reports.items() if report['issues']}
        assert not failures, failures
        borders = {name: [sample for sample in report['borders'] if sample['ratio'] < 3] for name, report in reports.items()}
        assert not any(borders.values()), borders
        assert page.locator('dialog').evaluate_all("dialogs=>dialogs.every(dialog=>{const heading=document.getElementById(dialog.getAttribute('aria-labelledby'));return heading&&dialog.contains(heading)&&heading.textContent.trim();})")
        for width, height in ((1366, 900), (390, 900), (320, 256)):
            page.set_viewport_size({'width': width, 'height': height})
            page.locator('#create-user [name="username"]').focus()
            for _ in range(5):
                page.keyboard.press('Tab')
                focus = focus_snapshot(page)
                assert focus['keyboard'] and focus['outline'] >= 2 and focus['visible'] and focus['uncovered'], focus
            capture_preview(page, f'keyboard-{width}x{height}.png')
        page.set_viewport_size({'width': 390, 'height': 900})
        page.locator('#nav-toggle').focus()
        page.keyboard.press('Space')
        assert page.locator('#nav-toggle').get_attribute('aria-expanded') == 'true'
        page.keyboard.press('Escape')
        assert page.locator('#nav-toggle').evaluate('element=>element===document.activeElement')
        assert page.locator('#nav-toggle').get_attribute('aria-expanded') == 'false'
        page.evaluate("location.hash='agent-credentials'")
        page.locator('#agent-credentials').wait_for(state='visible')
        page.request.post(live_server + '/admin/agent-credentials', headers={'X-AssetGuard-Admin-Token': os.environ['ASSETGUARD_ADMIN_SHARED_SECRET']}, data={})
        page.locator('#refresh-agent-credentials').click()
        origin = page.locator('.revoke-agent-credential').first
        origin.wait_for()
        origin.focus()
        page.keyboard.press('Enter')
        dialog = page.get_by_role('dialog', name='Отозвать ключ Agent?', exact=True)
        dialog.wait_for()
        for width, height in ((390, 900), (320, 256)):
            page.set_viewport_size({'width': width, 'height': height})
            for key in ('Tab', 'Shift+Tab', 'Tab', 'Tab'):
                page.keyboard.press(key)
                focus = focus_snapshot(page)
                assert focus['inDialog'] and focus['visible'] and focus['uncovered'], focus
        page.keyboard.press('Escape')
        dialog.wait_for(state='hidden')
        assert origin.evaluate('element=>element===document.activeElement')
        assert page.evaluate('getComputedStyle(document.documentElement).scrollBehavior') == 'auto'
        browser.close()


def capture_preview(page, name):
    """Capture only the isolated fixture; never use this with production credentials."""
    output = os.environ.get('ASSETGUARD_UI_STAGE5_PREVIEW_DIR')
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(directory / name))
