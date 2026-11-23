"""Human review, adjudication and judge calibration workspace."""
import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Judge Calibration",page_icon="⚖️",layout="wide")
st.title("Human Adjudication & Judge Calibration")
st.caption("Collect expert criterion labels, resolve disagreements and quantify judge reliability.")
base=os.getenv("API_BASE_URL","https://llm-prompt-benchmark.onrender.com").rstrip("/")
with st.sidebar:
    key=st.text_input("Review API key",type="password")
    st.caption("Used only for authenticated review API requests.")
headers={"X-Review-API-Key":key}

def request(method,path,**kwargs):
    r=requests.request(method,base+path,headers=headers,timeout=60,**kwargs)
    r.raise_for_status()
    return r.json()

tab_review,tab_cal=st.tabs(["Human review & adjudication","Calibration report"])
with tab_review:
    st.subheader("Load a judge evaluation")
    evaluation_id=st.text_input("Rubric evaluation ID")
    if st.button("Load evaluation",disabled=not evaluation_id.strip()):
        try:
            payload=request("GET",f"/rubrics/evaluations/{evaluation_id}")
            st.session_state["human_review_eval"]=payload
            task=request("POST",f"/rubrics/evaluations/{evaluation_id}/review-task")
            st.success(f"Review task ready: {task['annotation_task_id']} · {task['status']}")
        except requests.RequestException as exc: st.error(str(exc))
    payload=st.session_state.get("human_review_eval")
    if payload:
        st.markdown("**Original prompt**")
        st.write(payload["prompt_text"])
        st.markdown("**Assistant response**")
        st.write(payload["response_text"])
        df=pd.DataFrame(payload["scores"])
        st.dataframe(df,use_container_width=True,hide_index=True)
        st.divider()
        st.subheader("Submit expert criterion label")
        ids=[r["component_id"] for r in payload["scores"]]
        component=st.selectbox("Criterion",ids)
        criterion=next(r for r in payload["scores"] if r["component_id"]==component)
        st.info(f"{criterion['parent_category']} · {criterion['criterion_name']}\n\n{criterion['evaluation_question']}")
        annotator=st.text_input("Expert / annotator ID")
        verdict=st.selectbox("Human verdict",["pass","fail","not_applicable"])
        evidence=st.text_area("Evidence from the response",height=90)
        rationale=st.text_area("Rationale",height=90)
        confidence=st.slider("Confidence",1,5,4)
        if st.button("Submit human annotation",disabled=not annotator.strip() or len(evidence.strip())<3):
            try:
                out=request("POST","/rubrics/human-annotations",json={"evaluation_id":payload["rubric_evaluation_id"],
                    "component_id":component,"annotator_id":annotator,"verdict":verdict,
                    "evidence":evidence,"rationale":rationale,"confidence":confidence})
                st.success(f"Annotation saved: {out['human_annotation_id']}")
            except requests.RequestException as exc: st.error(str(exc))
        st.divider()
        st.subheader("Adjudicate a criterion")
        st.caption("Use this when independent expert labels disagree or an authoritative final label is required.")
        adjudicator=st.text_input("Adjudicator ID")
        final_verdict=st.selectbox("Final adjudicated verdict",["pass","fail","not_applicable"],key="final_verdict")
        final_evidence=st.text_area("Adjudication evidence",key="final_evidence")
        notes=st.text_area("Adjudication notes",key="adjudication_notes")
        if st.button("Save final adjudication",disabled=not adjudicator.strip() or len(final_evidence.strip())<3):
            try:
                out=request("POST","/rubrics/adjudications",json={"evaluation_id":payload["rubric_evaluation_id"],
                    "component_id":component,"adjudicator_id":adjudicator,"verdict":final_verdict,
                    "evidence":final_evidence,"notes":notes})
                st.success(f"Final label saved: {out['final_verdict']}")
            except requests.RequestException as exc: st.error(str(exc))

with tab_cal:
    st.subheader("Compare judge labels with expert labels")
    rubric_id=st.text_input("Optional rubric ID (leave blank for all rubrics)")
    min_samples=st.number_input("Minimum samples per criterion",min_value=2,max_value=1000,value=5)
    agreement=st.slider("Minimum exact agreement",0.0,1.0,0.80,0.05)
    save=st.checkbox("Save calibration run to Neon",value=True)
    if st.button("Run calibration",type="primary"):
        try:
            payload=request("POST","/rubrics/calibration",json={"rubric_id":rubric_id or None,
                "min_samples":int(min_samples),"reliability_threshold":agreement,"save_run":save})
            st.session_state["calibration_report"]=payload
        except requests.RequestException as exc: st.error(str(exc))
    report=st.session_state.get("calibration_report")
    if report:
        overall=report["overall"]
        a,b,c=st.columns(3)
        a.metric("Compared labels",overall["sample_count"])
        b.metric("Exact agreement",overall["exact_agreement"] if overall["exact_agreement"] is not None else "—")
        c.metric("Cohen's kappa",overall["cohen_kappa"] if overall["cohen_kappa"] is not None else "—")
        st.caption(report["method"])
        if report.get("calibration_run_id"): st.caption("Saved calibration run: "+report["calibration_run_id"])
        results=pd.DataFrame(report["criteria"])
        if not results.empty:
            st.dataframe(results,use_container_width=True,hide_index=True)
            flagged=results[results["reliability_status"]!="reliable"]
            st.subheader("Criteria requiring attention")
            if flagged.empty: st.success("No criteria crossed the configured reliability thresholds.")
            else: st.warning(f"{len(flagged)} criteria need more labels or review.")
            st.dataframe(flagged,use_container_width=True,hide_index=True)
        else:
            st.info("No comparable expert/adjudicated labels yet. Submit human annotations or adjudications first.")
