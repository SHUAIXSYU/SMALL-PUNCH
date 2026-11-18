"""Finite-refinement ranking screen; never a rigorous numerical error bound."""
import math


def screen(original_d01, original_i08, refined_d01, refined_i08):
    values=(original_d01,original_i08,refined_d01,refined_i08)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in values):
        raise ValueError("Four finite nonnegative actual Loss values required")
    gap=original_i08-original_d01
    if gap<=0:raise ValueError("Frozen baseline must have D01 ranked before I08")
    d=refined_d01-original_d01;i=refined_i08-original_i08
    total=abs(d)+abs(i)
    return {"original_gap":gap,"delta_loss_d01":d,"delta_loss_i08":i,
            "sum_abs_loss_changes":total,"ratio_to_original_gap":total/gap,
            "screen":"OBSERVED_CHANGES_SMALLER_THAN_GAP" if total<gap else "RANKING_SENSITIVE_REVIEW",
            "refined_gap_i08_minus_d01":refined_i08-refined_d01,
            "observed_refined_ranking":"D01_FIRST" if refined_d01<refined_i08 else "I08_FIRST" if refined_i08<refined_d01 else "TIED",
            "not_a_rigorous_error_bound":True,
            "scope":"Two observed refinements only; use after independent identity and numerical qualification"}
