"""Mapa real, inspeção de respostas e proveniência explícita dos destinos."""
import math, unicodedata, html
import folium

def valid_point(p):
    return isinstance(p,dict) and all(isinstance(p.get(k),(float,int)) and not isinstance(p[k],bool) and math.isfinite(p[k]) and abs(p[k])<=bound for k,bound in [('lat',90),('lng',180)])

def destination_for(record, places, illustrative=False):
    a=record['answers']
    if valid_point(a.get('q15_point')):
        return dict(a['q15_point'],name=a.get('q15') or 'Destino informado',provenance='Coordenada informada na resposta')
    norm=lambda x: ''.join(c for c in unicodedata.normalize('NFD',str(x or '')) if unicodedata.category(c)!='Mn').strip().lower()
    aliases={'pva':'8222713258','pavilhao de aulas i':'8222713258','pvb':'21450486','bct':'292666798','biblioteca central':'292666798','bernardao':'148819551','reitoria':'148819551'}
    name=norm(a.get('q15'))
    for p in places:
        if norm(p['name'])==name or p['id']==aliases.get(name):
            return dict(p,provenance='Nome associado ao catálogo OpenStreetMap')
    if illustrative and record.get('is_synthetic') is True:
        chosen={'Destino fictício A':'292666798','Destino fictício B':'8222713258','Destino fictício C':'148819551'}.get(a.get('q15'))
        for p in places:
            if p['id']==chosen:return dict(p,illustrative=True,provenance='ATRIBUIÇÃO ILUSTRATIVA. Não é um destino real informado na resposta.')
    return None

def territorial_map(records, catalog, campus, response_id='', illustrative=False, streets=None):
    """Nunca geocodifica endereços nem envia respostas a um serviço de rotas."""
    m=folium.Map(location=[-20.758,-42.875],zoom_start=14,tiles='OpenStreetMap',control_scale=True,scrollWheelZoom=False)
    folium.GeoJson(campus,name='Campus UFV — contorno colaborativo',style_function=lambda _:dict(color='#a37900',weight=3,fillColor='#d1a705',fillOpacity=.15),tooltip='UFV · contorno OSM, não cadastral').add_to(m)
    if streets:
        folium.GeoJson(streets,name='Ruas vetoriais OSM (funcionam sem imagens do mapa)',show=False,style_function=lambda _:dict(color='#8a8a82',weight=1)).add_to(m)
    landmarks=folium.FeatureGroup(name='Referências reais da UFV').add_to(m)
    for p in catalog['places']:
        folium.CircleMarker([p['lat'],p['lng']],radius=5,color='#8e6c00',fill=True,fill_opacity=1,fill_color='#d1a705',tooltip=html.escape(p['name'])).add_to(landmarks)
    origins=folium.FeatureGroup(name='Origens no recorte').add_to(m)
    for r in records:
        a=r['answers'];o=(a.get('q11') or {}).get('point')
        if not valid_point(o):continue
        popup='<b>'+html.escape(r['response_id'])+'</b><br>'+html.escape(str(a.get('q16') or 'Meio não informado'))+'<br>Destino original: '+html.escape(str(a.get('q15') or 'Não informado'))
        folium.CircleMarker([o['lat'],o['lng']],radius=4,color='#901812',weight=1,fill=True,fill_opacity=.65,popup=folium.Popup(popup,max_width=280),tooltip=html.escape(r['response_id'])).add_to(origins)
    chosen=next((r for r in records if r['response_id']==response_id),None)
    if chosen:
        a=chosen['answers'];o=(a.get('q11') or {}).get('point');d=destination_for(chosen,catalog['places'],illustrative);points=[]
        if valid_point(o):
            points.append([o['lat'],o['lng']]);folium.CircleMarker(points[-1],radius=10,color='#901812',weight=4,tooltip='Origem selecionada').add_to(m)
        if d:
            points.append([d['lat'],d['lng']]);folium.CircleMarker(points[-1],radius=9,color='#246480',weight=4,tooltip=html.escape(d['name']),popup=html.escape(d['provenance'])).add_to(m)
        if len(points)==2:folium.PolyLine(points,color='#246480',dash_array='7 9',tooltip='Ligação origem–destino; não é rota percorrida').add_to(m)
        if points:m.fit_bounds(points,max_zoom=16,padding=(35,35))
    folium.LayerControl(collapsed=False).add_to(m)
    return m
