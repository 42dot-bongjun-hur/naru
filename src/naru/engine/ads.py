from .templates import render_template


def render_ad(
    slot_id: str,
    ad_format: str = "auto",
    full_width_responsive: bool = True
) -> str:
    """구글 애드센스 표준 반응형 광고 단위 생성"""
    if not slot_id:
        return ""
    return render_template(
        "partial_ad.html", slot_id=slot_id, ad_format=ad_format,
        full_width_responsive=full_width_responsive, infeed=False, layout_key="",
    )

def render_infeed_ad(slot_id: str, layout_key: str = "") -> str:
    """카드 그리드 내 인피드 광고 전용 렌더러"""
    if not slot_id:
        return ""
    return render_template(
        "partial_ad.html", slot_id=slot_id, ad_format="fluid",
        infeed=True, layout_key=layout_key,
    )
