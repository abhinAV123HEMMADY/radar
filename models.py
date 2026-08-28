from pydantic import BaseModel, Field
from typing import List


class SourceCitation(BaseModel):
    url: str = Field(description="URL of the source")
    summary: str = Field(
        description=(
            "Write the actual facts from this source as a short statement — include real numbers, "
            "feature names, or direct claims. "
            "GOOD: '$11.99/month for Prime members, $14.99 standalone; includes offline listening and HD audio.' "
            "BAD: 'Outlines Amazon Music pricing structure.' or 'Describes the pricing plans.'"
        )
    )


class DimensionData(BaseModel):
    content: str = Field(description="Analysis of this competitive dimension")
    sources: List[SourceCitation] = Field(
        default_factory=list,
        description="URLs that back up this analysis"
    )


class CompetitorAnalysis(BaseModel):
    name: str = Field(description="Competitor company or product name")
    website: str = Field(default="", description="Competitor's main website")
    pricing: DimensionData = Field(description="Pricing model, tiers, and costs")
    key_features: DimensionData = Field(description="Core product features and capabilities")
    market_positioning: DimensionData = Field(description="How they position and differentiate themselves")
    target_audience: DimensionData = Field(description="Who their customers are and what problems they solve")
    recent_developments: DimensionData = Field(description="News, launches, or changes in the last 6-12 months")
    key_threats: List[str] = Field(
        default_factory=list,
        description=(
            "3-5 specific threats this competitor poses — name the exact feature, bundle, or "
            "strategy that is the threat. "
            "GOOD: 'Amazon Music bundles with Prime ($139/yr), making it free for 200M+ Prime members — "
            "Spotify cannot match this zero-marginal-cost acquisition channel.' "
            "BAD: 'Amazon has a large customer base that could hurt Spotify.'"
        ),
    )
    opportunities: List[str] = Field(
        default_factory=list,
        description=(
            "3-5 specific weaknesses in this competitor's product that the company being analysed "
            "can exploit — name the actual missing or inferior feature and what to do about it. "
            "GOOD: 'Amazon Music has no social/collaborative playlist feature; Spotify should "
            "double down on Blend and group sessions to lock in users Amazon cannot retain.' "
            "BAD: 'Spotify can improve its features to compete with Amazon.'"
        ),
    )


class PrioritizedAction(BaseModel):
    action: str = Field(description="Concrete next step based on this analysis")
    impact: int = Field(
        ge=1, le=5,
        description="1-5: how much this moves competitive position if executed (5 = highest impact)",
    )
    effort: int = Field(
        ge=1, le=5,
        description="1-5: engineering/GTM effort required to execute (5 = highest effort)",
    )
    rationale: str = Field(
        default="",
        description="One sentence on why this impact/effort score was assigned",
    )


class CompetitorSupportLevel(BaseModel):
    competitor: str = Field(description="Competitor company name")
    level: str = Field(description="Exactly one of: 'Yes', 'No', 'Partial'")


class FeatureComparisonRow(BaseModel):
    feature: str = Field(description="Name of the feature or capability being compared")
    support: List[CompetitorSupportLevel] = Field(
        description="One entry per competitor with its support level for this feature."
    )


class BriefingOverview(BaseModel):
    """Cross-competitor parts of the briefing, generated in one call alongside the
    per-competitor profiles (generated concurrently, one call each) — splitting the
    single large generation this way runs them all in parallel instead of forcing
    the model to emit every competitor's profile serially in one giant response."""
    executive_summary: str = Field(description="2-3 paragraph overview of the competitive landscape")
    feature_comparison: List[FeatureComparisonRow] = Field(
        default_factory=list,
        description=(
            "5-8 rows comparing key features across ALL competitors, e.g. 'Free tier', 'API access', "
            "'Mobile app', 'Collaboration tools', 'AI features'. Every competitor must have an entry "
            "in each row's support list."
        ),
    )
    recommended_actions: List[PrioritizedAction] = Field(
        description="Concrete next steps based on this analysis, each scored for impact and effort"
    )


class CompetitiveBriefing(BaseModel):
    company: str = Field(description="The company being analyzed")
    executive_summary: str = Field(description="2-3 paragraph overview of the competitive landscape")
    competitors: List[CompetitorAnalysis] = Field(description="Detailed analysis of each competitor")
    feature_comparison: List[FeatureComparisonRow] = Field(
        default_factory=list,
        description=(
            "5-8 rows comparing key features across ALL competitors, e.g. 'Free tier', 'API access', "
            "'Mobile app', 'Collaboration tools', 'AI features'. Every competitor must have an entry "
            "in each row's support list."
        ),
    )
    recommended_actions: List[PrioritizedAction] = Field(
        description="Concrete next steps based on this analysis, each scored for impact and effort"
    )
