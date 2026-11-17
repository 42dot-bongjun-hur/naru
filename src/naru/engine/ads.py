from . import config as engine_config


def render_ad(
    slot_id: str,
    ad_format: str = "auto",
    full_width_responsive: bool = True
) -> str:
    """구글 애드센스 표준 반응형 광고 단위 생성"""
    if not slot_id:
        return ""
    full_width_value = "true" if full_width_responsive else "false"
    return f"""<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="{engine_config.ADSENSE_PUB_ID}"
     data-ad-slot="{slot_id}"
     data-ad-format="{ad_format}"
     data-full-width-responsive="{full_width_value}"></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({{}});
</script>"""

def render_infeed_ad(slot_id: str, layout_key: str = "") -> str:
    """카드 그리드 내 인피드 광고 전용 렌더러"""
    if not slot_id:
        return ""
    layout_attr = f'data-ad-layout-key="{layout_key}"' if layout_key else 'data-ad-format="fluid"'
    return f"""<ins class="adsbygoogle"
     style="display:block"
     data-ad-client="{engine_config.ADSENSE_PUB_ID}"
     data-ad-slot="{slot_id}"
     {layout_attr}></ins>
<script>
     (adsbygoogle = window.adsbygoogle || []).push({{}});
</script>"""
