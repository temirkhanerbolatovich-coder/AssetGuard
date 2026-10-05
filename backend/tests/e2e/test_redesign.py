"""Real local workflows and screenshots of disposable data for the Ledger redesign."""
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from test_dashboard import live_server, capture_redesign_preview as capture
from test_ui_acceptance import seed_school, MEASURE_CONTRAST
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.snapshots.models import ManagedEndpointRecord

pytestmark = pytest.mark.skipif(os.environ.get('ASSETGUARD_RUN_BROWSER_E2E') != '1', reason='Browser checks are opt-in.')


def log_in(page, server, route='devices'):
    page.goto(server + '/#' + route)
    page.locator('#login-mode').click()
    page.locator('#token').fill(os.environ['ASSETGUARD_ADMIN_SHARED_SECRET'])
    page.locator('#login').click()
    page.locator('#status').filter(has_text='Данные актуальны').wait_for()


def seed_registry():
    with get_session_factory()() as session:
        organization, room, assets = seed_school(session, 'Лицей — учебный корпус', 24)
        assets[0].name = 'Шкаф для учебных пособий — очень длинное русское название с дополнительным описанием'
        session.add(ManagedEndpointRecord(source='TEST', organization_id=organization.id,
            hostname='PC-Учительская-01', status='ONLINE', last_seen_at=datetime.now(UTC),
            created_at=datetime.now(UTC), updated_at=datetime.now(UTC)))
        room_id = str(room.id)
        session.commit()
    return room_id


def test_registry_source_views_drawer_retry_and_link_are_real(live_server):
    playwright = pytest.importorskip('playwright.sync_api')
    room_id = seed_registry()
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        context = browser.new_context(viewport={'width':1440,'height':1000}, permissions=['clipboard-read','clipboard-write'])
        page = context.new_page()
        page.set_default_timeout(10000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        log_in(page, live_server)
        page.evaluate('document.fonts.ready')
        capture(page, 'registry-desktop.png')
        assert page.locator('#assets tr').count() == 20
        assert 'Не связано' not in page.locator('#assets').inner_text()
        assert not page.locator('#assets .hardware-brief').count()
        page.locator('[data-registry-view=computers]').click()
        assert page.locator('#assets tr').count() == 1
        page.locator('#assets .open-computer').click()
        page.locator('#computer-title').filter(has_text='PC-Учительская-01').wait_for()
        assert page.locator('#computer-meta').get_by_text('Обнаружен Agent.',exact=False).is_visible()
        page.locator('#computer-detail').get_by_text('Идентификаторы компьютера',exact=True).click()
        page.locator('#computer-identifiers').locator('.copy-value').click()
        assert page.evaluate('navigator.clipboard.readText()')
        capture(page,'computer-desktop.png')
        page.locator('#computer-detail a[href="#devices"]').click()
        page.locator('#devices').wait_for(state='visible')
        page.locator('[data-registry-view=assets]').click()
        page.locator('#device-search').fill('Шкаф')
        assert page.locator('#assets tr').count() == 1
        page.locator('#assets .device-open-link').focus()
        page.keyboard.press('Enter')
        page.locator('#detail-key-facts').get_by_text('Кабинет 101', exact=True).wait_for()
        capture(page, 'asset-desktop.png')
        page.locator('#detail-back').click()
        assert page.locator('#device-search').input_value() == 'Шкаф'
        assert page.locator('[data-registry-view=assets]').get_attribute('aria-pressed') == 'true'
        page.locator('#show-create').click()
        form = page.locator('#create-asset')
        assert form.locator('[name=name]').bounding_box()['width'] > 300
        assert form.locator('[name=name]').evaluate("field=>field.labels[0].querySelector('.field-caption .required-marker')!==null")
        form.locator('[name=inventory_number]').fill('IT-001')
        form.locator('[name=name]').fill('Компьютер учительской')
        form.locator('[name=room_id]').select_option(room_id)
        posts = []

        def reject_once(route):
            posts.append(route.request.method)
            assert form.get_by_role('button', name='Сохраняем…').is_disabled()
            # A repeated submit event must not create a second request.
            form.evaluate("form=>form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true}))")
            route.fulfill(status=409,json={'detail':'Этот инвентарный номер уже используется. Укажите другой.'})

        page.route('**/admin/assets', reject_once)
        form.get_by_role('button', name='Сохранить имущество').click()
        form.locator('.form-error').wait_for(state='visible')
        assert posts == ['POST']
        assert form.locator('[name=name]').input_value() == 'Компьютер учительской'
        assert form.locator('[name=inventory_number]').input_value() == 'IT-001'
        capture(page, 'create-error-desktop.png')
        page.unroute('**/admin/assets', reject_once)
        form.locator('[name=inventory_number]').fill('IT-002')
        form.get_by_role('button', name='Сохранить имущество').click()
        page.locator('#asset-create-dialog').wait_for(state='hidden')
        page.locator('#status').filter(has_text='Данные актуальны').wait_for()
        page.locator('#device-search').fill('')
        page.locator('[data-registry-view=unlinked]').click()
        page.locator('#assets .link-endpoint').click()
        page.locator('#link-choice-details').get_by_text('IT-002',exact=True).wait_for()
        assert '101' in page.locator('#link-choice-details').inner_text()
        capture(page,'link-desktop.png')
        page.locator('#link-confirm').click()
        page.locator('#link-dialog').wait_for(state='hidden')
        page.locator('#registry-unlinked-count').filter(has_text='0').wait_for()
        page.locator('[data-registry-view=computers]').click()
        assert page.locator('#assets .relation-label').inner_text() == 'Связан с Agent'
        page.locator('#assets .device-open-link').click()
        page.locator('#detail-key-facts').get_by_text('PC-Учительская-01',exact=True).wait_for()
        assert not errors, errors
        context.close(); browser.close()


@pytest.mark.parametrize('motion',['reduce','no-preference'])
def test_complete_workspace_reflow_fonts_onboarding_and_comparison(live_server, motion):
    playwright = pytest.importorskip('playwright.sync_api')
    room_id = seed_registry()
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1000},reduced_motion=motion)
        page.set_default_timeout(10000)
        page.goto(live_server)
        page.evaluate('document.fonts.ready')
        if motion == 'reduce': capture(page,'login-desktop.png')
        log_in(page,live_server,'overview')
        assert page.locator('#setup-guide').is_hidden()
        page.locator('#setup-help').click()
        assert page.locator('#setup-guide').is_visible()
        assert page.locator('#setup-progress').inner_text() == '2 из 2 основных шагов'
        page.locator('#setup-help').click()
        assert page.locator('#setup-guide').is_hidden()
        if motion == 'reduce': capture(page,'overview-desktop.png')
        page.locator('#collapse-navigation').click()
        assert page.locator('body').get_attribute('class') == 'navigation-collapsed'
        assert page.locator('#main-nav a').evaluate_all("links=>links.every(link=>link.title.trim())")
        page.locator('#collapse-navigation').click()
        for route in ('devices','incidents','locations','location-access','agent-credentials','data-exchange','vision','agent-workflow'):
            page.evaluate('route=>location.hash=route',route)
            page.locator('#'+route).wait_for(state='visible')
            page.evaluate('document.fonts.ready')
            assert not page.evaluate(MEASURE_CONTRAST)['issues'], route
            if motion == 'reduce': capture(page,route+'-desktop.png')
            for width in (360,390,768,1024,1120,1199,1200,1280,1440,1920):
                page.set_viewport_size({'width':width,'height':1000})
                assert page.locator('body').evaluate('element=>element.scrollWidth<=element.clientWidth'), (route,width)
                if width >= 1200:
                    assert page.locator('#main-nav').bounding_box()['y'] < page.locator('#collapse-navigation').bounding_box()['y'], (route,width)
                    assert page.locator('#nav-toggle').is_hidden(), (route,width)
                else:
                    assert page.locator('#main-nav').is_hidden(), (route,width)
                    assert page.locator('#nav-toggle').is_visible(), (route,width)
                    assert page.locator('#app-header').bounding_box()['height'] < 200, (route,width)
                if width == 390 and motion == 'reduce': capture(page,route+'-mobile.png')
            page.set_viewport_size({'width':1440,'height':1000})
        page.evaluate('room=>location.hash="room="+room',room_id)
        page.locator('#room-detail').wait_for(state='visible')
        if motion == 'reduce': capture(page,'room-desktop.png')
        page.evaluate("location.hash='devices'")
        page.locator('#devices').wait_for(state='visible')
        page.locator('#show-create').click()
        if motion == 'reduce': capture(page,'create-desktop.png')
        page.set_viewport_size({'width':390,'height':844})
        if motion == 'reduce': capture(page,'create-mobile.png')
        page.keyboard.press('Escape')
        assert page.locator('#show-create').evaluate('element=>element===document.activeElement')
        page.set_viewport_size({'width':1440,'height':1000})
        assert page.evaluate('getComputedStyle(document.documentElement).fontSynthesis') == 'none'
        client = page.context.new_cdp_session(page)
        client.send('DOM.enable'); client.send('CSS.enable')
        document = client.send('DOM.getDocument')['root']['nodeId']
        node = client.send('DOM.querySelector',{'nodeId':document,'selector':'.device-open-link'})['nodeId']
        fonts = client.send('CSS.getPlatformFontsForNode',{'nodeId':node})['fonts']
        assert fonts and all(font['isCustomFont'] and 'Golos' in font['familyName'] for font in fonts), fonts
        comparison = page.evaluate("""renderFieldComparison('RAM',{previous:{capacity:8192,speed:3200,numslots:0,description:'DDR4'},current:{capacity:0,speed:0,numslots:0,description:'DDR4 DIMM'}})""")
        assert 'Не указан' in comparison and 'Нет данных' not in comparison
        assert '<td>Слот</td><td>0</td><td>0</td>' in comparison
        assert 'не подтверждает замену' in comparison
        missing = page.evaluate("renderFieldComparison('RAM',{previous:{capacity:8192,serial:'OLD'},current:null})")
        assert 'Нет данных' in missing and 'Компонент не представлен' in missing
        assert 'Отсутствует' not in missing
        if motion == 'reduce':
            assert page.locator('.device-open-link').first.evaluate('element=>getComputedStyle(element).transitionDuration') == '0s'
        browser.close()


def test_unlinked_computer_shows_received_hardware_and_retries(live_server):
    playwright = pytest.importorskip('playwright.sync_api')
    fixture = Path(__file__).parents[1] / 'fixtures/glpi-agent-minimal-sanitized.json'
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={'width':1440,'height':1000})
        page.set_default_timeout(10000)
        headers = {'X-AssetGuard-Ingest-Token':os.environ['ASSETGUARD_INVENTORY_SHARED_SECRET'],
            'X-AssetGuard-Source':'GLPI_AGENT','X-AssetGuard-Source-Version':'1.19',
            'X-AssetGuard-Schema-Version':'redesign-test','X-AssetGuard-Inventory-Type':'FULL',
            'X-AssetGuard-Idempotency-Key':'redesign-computer-first'}
        result = page.request.post(live_server+'/internal/inventories',headers=headers,data=json.loads(fixture.read_text(encoding='utf-8')))
        assert result.ok
        snapshot = page.request.get(live_server+'/admin/snapshots/'+result.json()['snapshot_id'],headers={'X-AssetGuard-Admin-Token':os.environ['ASSETGUARD_ADMIN_SHARED_SECRET']}).json()
        endpoint_id = snapshot['endpoint_id']
        log_in(page,live_server,'computer='+endpoint_id)
        page.locator('#computer-content').wait_for(state='visible')
        assert page.locator('#computer-hardware .hardware-card').count() >= 3
        assert page.locator('#computer-hardware').get_by_role('heading',name='Оперативная память').is_visible()
        assert page.locator('#computer-hardware').get_by_text('4 ГБ памяти',exact=True).is_visible()
        assert page.evaluate("componentMeta({type:'GPU',raw_data:{memory:4096}})[0]") == '4 ГБ памяти'
        capture(page,'computer-hardware-desktop.png')
        page.locator('#computer-detail').get_by_text('История проверок и изменений',exact=True).click()
        assert page.locator('#computer-history').get_by_text('Инвентаризация завершена',exact=True).is_visible()
        page.reload()
        page.locator('#computer-content').wait_for(state='visible')
        assert page.url.endswith('#computer='+endpoint_id)
        page.locator('#computer-detail a[href="#devices"]').click()
        page.route('**/admin/endpoints/'+endpoint_id,lambda route:route.fulfill(status=503,json={'detail':'Повторите загрузку компьютера.'}))
        page.reload()
        page.locator('#assets .open-computer').click()
        page.locator('#computer-error').wait_for(state='visible')
        page.unroute('**/admin/endpoints/'+endpoint_id)
        page.locator('#computer-actions').get_by_role('button',name='Повторить').click()
        page.locator('#computer-content').wait_for(state='visible')
        page.set_viewport_size({'width':390,'height':844})
        assert page.locator('body').evaluate('element=>element.scrollWidth<=element.clientWidth')
        capture(page,'computer-hardware-mobile.png')
        browser.close()


def test_actual_browser_zoom_200_percent_keeps_forms_usable(live_server, tmp_path):
    """Use Chrome's zoom API, rather than CSS zoom or device-scale emulation."""
    playwright = pytest.importorskip('playwright.sync_api')
    seed_registry()
    extension = tmp_path / 'zoom-extension'
    extension.mkdir()
    (extension / 'manifest.json').write_text(json.dumps({
        'manifest_version':3,'name':'Isolated browser zoom check','version':'1.0',
        'permissions':['tabs'],'background':{'service_worker':'worker.js'},
    }),encoding='utf-8')
    (extension / 'worker.js').write_text('chrome.runtime.onInstalled.addListener(()=>{});',encoding='utf-8')
    with playwright.sync_playwright() as runtime:
        context = runtime.chromium.launch_persistent_context(str(tmp_path / 'browser-profile'),
            channel='chromium', headless=True, viewport={'width':1440,'height':1000},
            args=['--disable-extensions-except='+str(extension),'--load-extension='+str(extension)])
        worker = context.service_workers[0] if context.service_workers else context.wait_for_event('serviceworker')
        page = context.new_page()
        log_in(page,live_server)
        zoom = worker.evaluate("""async origin=>{const tabs=await chrome.tabs.query({});const tab=tabs.find(tab=>tab.url.startsWith(origin));await chrome.tabs.setZoom(tab.id,2);return await chrome.tabs.getZoom(tab.id)}""",live_server)
        assert zoom == 2
        page.wait_for_function('devicePixelRatio===2 && innerWidth===720')
        for route in ('devices','overview','incidents','locations','data-exchange','agent-credentials','location-access'):
            page.evaluate('route=>location.hash=route',route)
            page.locator('#'+route).wait_for(state='visible')
            assert page.locator('body').evaluate('element=>element.scrollWidth<=element.clientWidth'), route
        page.evaluate("location.hash='devices'")
        page.locator('#show-create').click()
        page.locator('#create-asset [name=name]').fill('Имущество при масштабе 200%')
        page.locator('#create-asset [type=submit]').click()
        page.locator('#create-asset .field-error').wait_for(state='visible')
        assert page.locator('#create-asset [name=name]').input_value() == 'Имущество при масштабе 200%'
        assert page.locator('#asset-create-dialog').evaluate('element=>element.getBoundingClientRect().right<=innerWidth')
        capture(page,'create-zoom-200.png')
        page.keyboard.press('Escape')
        assert page.locator('#show-create').evaluate('element=>element===document.activeElement')
        context.close()
