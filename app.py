"""AegisImage — Streamlit Forensic Analysis Interface.

Per docs/architecture.md, docs/rules.md, and docs/design.md:
- Presentation and event flow only; forensic logic lives in src/.
- Displays exact original image and derived artifacts separately and labels them.
- Prominently displays original SHA-256 hash.
- Provides PDF and JSON report downloads from the unified AnalysisReport object.
- Strictly adheres to the calm, evidence-oriented design system.
"""

from pathlib import Path
from typing import Any, Optional
import streamlit as st

from src.analysis import analyze_image
from src.config import (
    APP_NAME,
    APP_VERSION,
    DEFAULT_ELA_AMPLIFICATION,
    DEFAULT_ELA_QUALITY,
    MAX_UPLOAD_SIZE_BYTES,
    OVERALL_NOTICE,
    SUPPORTED_FORMATS,
)
from src.exceptions import ForensicError
from src.models import AnalysisReport, FileFacts, MethodResult, MethodStatus
from src.reporting import export_json, export_pdf, generate_export_filename

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title=f"{APP_NAME} — Image Forensics Toolkit",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- CSS Styling (Design Tokens per docs/design.md) ---
CUSTOM_CSS = """
<style>
/* Design tokens */
:root {
    --canvas: #F4F7FA;
    --surface: #FFFFFF;
    --ink: #14212B;
    --muted: #526371;
    --line: #D8E1E8;
    --accent: #087E8B;
    --accent-soft: #DDF4F4;
    --success: #216E4E;
    --warning: #8A5A00;
    --danger: #A52B34;
}

body {
    color: var(--ink);
    background-color: var(--canvas);
}

.main-header {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--line);
}

.app-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--ink);
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-bottom: 0.25rem;
}

.app-tagline {
    font-size: 1rem;
    color: var(--muted);
    line-height: 1.4;
    margin-bottom: 0.5rem;
}

.notice-banner {
    background-color: var(--accent-soft);
    border-left: 4px solid var(--accent);
    padding: 0.75rem 1rem;
    border-radius: 4px;
    font-size: 0.88rem;
    color: var(--ink);
    margin-bottom: 1.5rem;
}

.status-badge {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.status-completed {
    background-color: #E8F5E9;
    color: #216E4E;
    border: 1px solid #A5D6A7;
}

.status-not_applicable {
    background-color: #ECEFF1;
    color: #526371;
    border: 1px solid #CFD8DC;
}

.status-failed {
    background-color: #FFEBEE;
    color: #A52B34;
    border: 1px solid #FFCDD2;
}

.review-cue-card {
    background-color: #FFFDE7;
    border: 1px solid #FFF59D;
    border-left: 4px solid var(--warning);
    padding: 0.6rem 0.9rem;
    border-radius: 4px;
    font-size: 0.85rem;
    color: var(--ink);
    margin: 0.5rem 0;
}

.limitation-box {
    font-size: 0.82rem;
    color: var(--muted);
    font-style: italic;
    margin-top: 0.75rem;
    border-top: 1px dashed var(--line);
    padding-top: 0.5rem;
}

.artifact-caption {
    text-align: center;
    font-size: 0.78rem;
    color: var(--muted);
    font-style: italic;
    margin-top: 0.35rem;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_header() -> None:
    """Render application header and normative educational notice."""
    st.markdown(
        f"""
        <div class="main-header">
            <div class="app-title">🛡️ {APP_NAME} <span style="font-size: 0.9rem; font-weight: 400; color: #526371;">v{APP_VERSION}</span></div>
            <div class="app-tagline">
                Local-first digital image forensics toolkit for evidence inspection, SHA-256 integrity verification,
                JPEG Error Level Analysis, color statistics, and structured reporting.
            </div>
        </div>
        <div class="notice-banner">
            <b>Educational Forensic Notice:</b> {OVERALL_NOTICE}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_evidence_identity(report: AnalysisReport, original_bytes: bytes) -> None:
    """Render original evidence preview and verified FileFacts."""
    st.subheader("1. Evidence Identity & Integrity")

    col_preview, col_facts = st.columns([1.1, 1.0], gap="large")

    with col_preview:
        st.markdown("**Original Upload (Source Bytes Preserved)**")
        st.image(original_bytes, use_container_width=True)
        st.markdown(
            '<div class="artifact-caption">Source image — bytes kept immutable in session memory</div>',
            unsafe_allow_html=True,
        )

    with col_facts:
        facts = report.file_facts
        st.markdown("**Cryptographic Integrity**")
        st.code(facts.sha256, language=None)
        st.caption(
            "SHA-256 calculated over the exact original uploaded file bytes before any decoding or transformation."
        )

        if facts.sha1 or facts.md5:
            with st.expander("Additional Forensic Digests (SHA-1 & MD5)"):
                st.markdown(f"**SHA-1:** `{facts.sha1}`")
                st.markdown(f"**MD5:** `{facts.md5}`")
                st.caption("Provided for cross-referencing with legacy forensic hashes and NSRL databases.")

        st.markdown("**Container & Dimensions**")
        facts_table = {
            "Property": [
                "Filename",
                "Detected Format",
                "File Size",
                "Resolution",
                "Color Mode",
                "Frame Count",
                "Analyzed At (UTC)",
            ],
            "Value": [
                facts.original_filename_display,
                facts.detected_format,
                f"{facts.size_bytes:,} bytes ({facts.size_bytes / 1024:.1f} KB)",
                f"{facts.width} × {facts.height} px ({facts.width * facts.height / 1_000_000:.2f} MP)",
                facts.mode,
                f"{facts.frame_count} (still image)",
                facts.analysis_timestamp_utc,
            ],
        }
        st.dataframe(facts_table, hide_index=True, use_container_width=True)


def render_metadata_section(result: MethodResult) -> None:
    """Render metadata inspection findings, GPS privacy state, and raw tags."""
    st.markdown(
        f'### Metadata Inspection &nbsp; <span class="status-badge status-{result.status.value}">{result.status.value}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Observation:** {result.summary}")

    for w in result.warnings:
        st.markdown(f'<div class="review-cue-card">⚠️ <b>Review Cue:</b> {w}</div>', unsafe_allow_html=True)

    obs = result.observations
    if obs.get("has_exif", False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Camera Make", obs.get("make") or "Unavailable")
            st.metric("Capture Time", obs.get("datetime_original") or "Unavailable")
        with col2:
            st.metric("Camera Model", obs.get("model") or "Unavailable")
            st.metric("Orientation", str(obs.get("orientation") or "Standard"))
        with col3:
            st.metric("Software Tag", obs.get("software") or "None")
            gps_label = "Detected (Coordinates Suppressed)" if obs.get("gps_present") and not obs.get("gps_coordinates") else ("Disclosed" if obs.get("gps_coordinates") else "Not Present")
            st.metric("Geotagging", gps_label)

        # Photographic exposure parameters if available
        if obs.get("iso") or obs.get("exposure_time") or obs.get("f_number") or obs.get("focal_length"):
            st.markdown("**Photographic Exposure Parameters**")
            exp1, exp2, exp3, exp4 = st.columns(4)
            with exp1:
                st.metric("ISO Speed", str(obs.get("iso") or "Unavailable"))
            with exp2:
                st.metric("Shutter Speed", str(obs.get("exposure_time") or "Unavailable"))
            with exp3:
                st.metric("Aperture", str(obs.get("f_number") or "Unavailable"))
            with exp4:
                st.metric("Focal Length", str(obs.get("focal_length") or "Unavailable"))

        # Explicit GPS coordinates display if intentionally unsuppressed
        if obs.get("gps_coordinates"):
            gps_info = obs["gps_coordinates"]
            st.success(
                f"📍 **Disclosed GPS Coordinates (Examiner View):** `{gps_info.get('formatted')}` "
                f"(Latitude: `{gps_info.get('latitude')}`, Longitude: `{gps_info.get('longitude')}`)"
            )

        raw_tags = obs.get("raw_tags", {})
        if raw_tags:
            with st.expander(f"View All Normalized EXIF Tags ({len(raw_tags)} tags)"):
                st.json(raw_tags)
    else:
        st.info("No EXIF metadata was found in the uploaded image container.")

    if result.limitations:
        st.markdown(
            f'<div class="limitation-box"><b>Limitations:</b> {" | ".join(result.limitations)}</div>',
            unsafe_allow_html=True,
        )


def render_ela_section(result: MethodResult, original_bytes: bytes, file_facts: FileFacts) -> None:
    """Render JPEG Error Level Analysis visualization, metrics, and caveats."""
    st.markdown(
        f'### JPEG Error Level Analysis (ELA) &nbsp; <span class="status-badge status-{result.status.value}">{result.status.value}</span>',
        unsafe_allow_html=True,
    )

    if result.status == MethodStatus.NOT_APPLICABLE:
        st.info(
            f"ℹ️ **Not Applicable:** {result.summary} "
            f"Non-JPEG images use lossless or different block compression; "
            f"applying JPEG recompression to them produces misleading artifacts."
        )
        if result.limitations:
            st.markdown(
                f'<div class="limitation-box"><b>Interpretive Guidance:</b> {" | ".join(result.limitations)}</div>',
                unsafe_allow_html=True,
            )
        return

    st.markdown(f"**Observation:** {result.summary}")

    for w in result.warnings:
        st.markdown(f'<div class="review-cue-card">🔍 <b>Review Cue:</b> {w}</div>', unsafe_allow_html=True)

    obs = result.observations
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric("Recompression Quality", f"{obs.get('quality', 90)}%")
    with col_m2:
        st.metric("Amplification", f"{obs.get('amplification', 10)}×")
    with col_m3:
        st.metric("Mean Error Level", f"{obs.get('mean_difference', 0.0):.3f}")
    with col_m4:
        st.metric("Max Error Level", f"{obs.get('max_difference', 0)}")

    # Interactive parameter adjustment
    with st.expander("⚙️ Interactive ELA Parameters (Recompression & Amplification Tuning)"):
        st.caption(
            "Error Level Analysis is an exploratory method whose visual response depends on the recompression quality "
            "and amplification factor. Adjust these parameters to observe error distribution across compression baselines."
        )
        c_q, c_amp, c_btn = st.columns([2, 2, 1])
        with c_q:
            new_q = st.slider(
                "Recompression Quality (%)",
                min_value=50,
                max_value=98,
                value=int(st.session_state.get("ela_quality", DEFAULT_ELA_QUALITY)),
                step=1,
                key="slider_ela_q",
            )
        with c_amp:
            new_amp = st.slider(
                "Amplification Factor",
                min_value=5,
                max_value=30,
                value=int(st.session_state.get("ela_amplification", DEFAULT_ELA_AMPLIFICATION)),
                step=1,
                key="slider_ela_amp",
            )
        with c_btn:
            st.write("")
            st.write("")
            if st.button("Apply Parameters", use_container_width=True):
                st.session_state["ela_quality"] = new_q
                st.session_state["ela_amplification"] = new_amp
                st.rerun()

    if result.artifact_bytes:
        col_orig, col_ela = st.columns(2, gap="medium")
        with col_orig:
            st.markdown("**Original Image Preview**")
            st.image(original_bytes, use_container_width=True)
            st.markdown('<div class="artifact-caption">Original evidence preview</div>', unsafe_allow_html=True)

        with col_ela:
            st.markdown("**ELA Difference Visualization**")
            st.image(result.artifact_bytes, use_container_width=True)
            st.markdown(
                '<div class="artifact-caption">Derived visualization artifact — brighter areas indicate higher compression error</div>',
                unsafe_allow_html=True,
            )

    if result.limitations:
        st.markdown(
            f'<div class="limitation-box"><b>Interpretive Guidance:</b> {" | ".join(result.limitations)}</div>',
            unsafe_allow_html=True,
        )


def render_statistics_section(result: MethodResult) -> None:
    """Render color channel histograms and numeric summaries."""
    st.markdown(
        f'### Image Statistics & Histograms &nbsp; <span class="status-badge status-{result.status.value}">{result.status.value}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Observation:** {result.summary}")

    for w in result.warnings:
        st.markdown(f'<div class="review-cue-card">📊 <b>Statistical Cue:</b> {w}</div>', unsafe_allow_html=True)

    col_chart, col_stats = st.columns([1.2, 0.8], gap="large")

    with col_chart:
        if result.artifact_bytes:
            st.image(result.artifact_bytes, use_container_width=True)
            st.markdown(
                '<div class="artifact-caption">Derived Matplotlib histogram plot (256 bins for Red, Green, Blue, and Luminance channels)</div>',
                unsafe_allow_html=True,
            )

    with col_stats:
        obs = result.observations
        ch_stats = obs.get("channel_statistics", {})
        if ch_stats:
            st.markdown("**Per-Channel Summary Statistics**")
            channels = ["Red", "Green", "Blue"]
            if "luminance" in ch_stats:
                channels.append("Luminance (Y)")

            def _get_val(ch_key: str, prop: str) -> Any:
                return ch_stats.get(ch_key, {}).get(prop, "-")

            summary_table = {
                "Channel": channels,
                "Mean": [_get_val("red", "mean"), _get_val("green", "mean"), _get_val("blue", "mean")]
                + ([_get_val("luminance", "mean")] if "luminance" in ch_stats else []),
                "Std Dev": [_get_val("red", "std_dev"), _get_val("green", "std_dev"), _get_val("blue", "std_dev")]
                + ([_get_val("luminance", "std_dev")] if "luminance" in ch_stats else []),
                "Min": [_get_val("red", "min"), _get_val("green", "min"), _get_val("blue", "min")]
                + ([_get_val("luminance", "min")] if "luminance" in ch_stats else []),
                "Max": [_get_val("red", "max"), _get_val("green", "max"), _get_val("blue", "max")]
                + ([_get_val("luminance", "max")] if "luminance" in ch_stats else []),
                "Median": [_get_val("red", "median"), _get_val("green", "median"), _get_val("blue", "median")]
                + ([_get_val("luminance", "median")] if "luminance" in ch_stats else []),
            }
            st.dataframe(summary_table, hide_index=True, use_container_width=True)

        st.markdown(
            f"**Aspect Ratio:** `{obs.get('aspect_ratio', 'N/A')}` &nbsp;|&nbsp; **Total Pixels:** `{obs.get('total_pixels', 0):,}`"
        )

    if result.limitations:
        st.markdown(
            f'<div class="limitation-box"><b>Limitations:</b> {" | ".join(result.limitations)}</div>',
            unsafe_allow_html=True,
        )


def render_exports(report: AnalysisReport) -> None:
    """Render PDF and JSON export triggers and session controls."""
    st.subheader("3. Forensic Export & Reporting")
    st.markdown(
        "Generate and download structured investigation reports directly from the verified session analysis object. "
        "Exports maintain identical cryptographic SHA-256 digests and exclude exact GPS coordinates."
    )

    pdf_bytes = export_pdf(report)
    json_str = export_json(report)

    display_name = report.file_facts.original_filename_display
    pdf_filename = generate_export_filename(display_name, "pdf", report.generated_at_utc)
    json_filename = generate_export_filename(display_name, "json", report.generated_at_utc)

    col_pdf, col_json, col_reset = st.columns([1, 1, 0.8], gap="medium")

    with col_pdf:
        st.download_button(
            label="📄 Download PDF Forensic Report",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True,
        )

    with col_json:
        st.download_button(
            label="📦 Download JSON Forensic Data",
            data=json_str,
            file_name=json_filename,
            mime="application/json",
            use_container_width=True,
        )

    with col_reset:
        if st.button("🔄 Clear Evidence Session", use_container_width=True):
            st.session_state.clear()
            st.rerun()


def main() -> None:
    """Main application lifecycle and event flow."""
    render_header()

    # Preset sample options for frictionless demonstration and review
    sample_presets = {
        "None (Custom Upload Below)": None,
        "Sample 01: Untouched Baseline (JPEG)": "sample_images/sample_01_untouched.jpg",
        "Sample 02: Recompressed Lower Quality (JPEG)": "sample_images/sample_02_recompressed.jpg",
        "Sample 03: Spliced Manipulation (JPEG)": "sample_images/sample_03_tampered_spliced.jpg",
        "Sample 04: Camera EXIF & Photoshop Tag (JPEG)": "sample_images/sample_04_with_exif.jpg",
        "Sample 05: Geotagged Image with GPS Metadata (JPEG)": "sample_images/sample_05_with_gps.jpg",
        "Sample 06: Metadata-Free Stripped Container (JPEG)": "sample_images/sample_06_metadata_free.jpg",
        "Sample 07: Clean Lossless Container (PNG)": "sample_images/sample_07_clean.png",
        "Sample 08: Lossy Still Container (WebP)": "sample_images/sample_08_clean.webp",
    }

    # Upload and controls bar
    col_uploader, col_privacy = st.columns([3, 1], gap="medium")

    with col_uploader:
        selected_preset = st.selectbox(
            "Load labelled test fixture (or choose Custom Upload)",
            options=list(sample_presets.keys()),
            index=0,
            help="Select a standardized synthetic test fixture for evaluation demonstrations, or select Custom Upload to upload an image file.",
        )
        uploaded_file = st.file_uploader(
            "Upload image for forensic analysis",
            type=["jpg", "jpeg", "png", "webp"],
            help=f"Accepts JPEG, PNG, or WebP still images up to {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MiB.",
        )

    with col_privacy:
        st.markdown("**Privacy Controls**")
        suppress_gps = st.checkbox(
            "Suppress GPS coordinates",
            value=True,
            help="Hides exact latitude/longitude coordinates in UI and exported reports to protect location privacy.",
        )

    # Determine input bytes and filename
    file_bytes: Optional[bytes] = None
    input_filename: Optional[str] = None

    if uploaded_file is not None:
        file_bytes = uploaded_file.getvalue()
        input_filename = uploaded_file.name
    elif selected_preset and sample_presets[selected_preset] is not None:
        preset_path = Path(sample_presets[selected_preset])
        if preset_path.exists():
            file_bytes = preset_path.read_bytes()
            input_filename = preset_path.name
            st.info(f"📁 Loaded evaluation fixture: **{selected_preset}**")

    if file_bytes is None:
        st.info(
            "👆 **Get started:** Upload an image above or select a labelled test fixture to begin forensic examination. "
            "Supported formats: **JPEG**, **PNG**, **WebP** (up to 10 MiB). "
            "All processing occurs locally in memory; no evidence is uploaded to external clouds or remote APIs."
        )
        return

    # Initialize ELA parameters in session state if not set
    if "ela_quality" not in st.session_state:
        st.session_state["ela_quality"] = DEFAULT_ELA_QUALITY
    if "ela_amplification" not in st.session_state:
        st.session_state["ela_amplification"] = DEFAULT_ELA_AMPLIFICATION

    try:
        with st.spinner("Analyzing image facts, metadata, error levels, and color channels..."):
            report = analyze_image(
                file_bytes,
                filename=input_filename,
                suppress_gps=suppress_gps,
                ela_quality=st.session_state["ela_quality"],
                ela_amplification=st.session_state["ela_amplification"],
            )
    except ForensicError as e:
        st.error(f"❌ **Intake Rejected:** {e.message}")
        return
    except Exception as e:
        st.error(f"❌ **Analysis Failed:** Unexpected error encountered: {e}")
        return

    st.success("✅ Analysis completed successfully. Evidence facts and observations recorded below.")

    # 1. Evidence Identity & Integrity
    render_evidence_identity(report, file_bytes)
    st.markdown("---")

    # 2. Forensic Analysis Methods
    st.subheader("2. Investigation Methods & Observations")
    tab_meta, tab_ela, tab_stats = st.tabs(
        ["📋 Metadata Inspection", "🔍 Error Level Analysis (ELA)", "📊 Channel Histograms & Statistics"]
    )

    with tab_meta:
        if "metadata" in report.method_results:
            render_metadata_section(report.method_results["metadata"])

    with tab_ela:
        if "ela" in report.method_results:
            render_ela_section(report.method_results["ela"], file_bytes, report.file_facts)

    with tab_stats:
        if "image_statistics" in report.method_results:
            render_statistics_section(report.method_results["image_statistics"])

    st.markdown("---")

    # 3. Report Exports
    render_exports(report)


if __name__ == "__main__":
    main()

