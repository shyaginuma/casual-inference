import pandas as pd
import plotly
import plotly.express as px

from casual_inference.statistical_testing import eval_ttest_significance, t_test


class ABTestEvaluator:
    def __init__(self) -> None:
        self.variant_col: str = ""
        self.stats: pd.DataFrame = None

    def evaluate(self, data: pd.DataFrame, unit_col: str, variant_col: str, metrics: list[str]) -> None:
        """calculate stats of A/B test and cache it into the class variable.
        At first, it only assumes metrics can handle by Welch's t-test.

        Parameters
        ----------
        data : pd.DataFrame
            Dataframe has randomization unit column, variant assignment column, and metrics columns.
            The data should have been aggregated by the randmization unit.
        unit_col : str
            A column name stores the randomization unit. something like user_id, session_id, ...
        variant_col : str
            A column name stores the variant assignment.
            The control variant should have value 1.
        metrics : list[str]
            Columns stores metrics you want to evaluate.
        """
        self.stats = t_test(data, unit_col, variant_col, metrics)
        self.variant_col = variant_col

    def summary_table(self, p_threshold: float = 0.05) -> pd.DataFrame:
        """return statistics summary.

        In the future, styling dataframe or add another visualization can be considered.

        Parameters
        ----------
        p_threshold : float, optional
            significance level, by default 0.05

        Returns
        -------
        pd.DataFrame
            stats summary
        """
        if self.stats is None:
            raise ValueError("A/B test statistics haven't been calculated. Please call evaluate() in advance.")

        stats = self.stats.copy(deep=True)
        significance, abs_ci_width, rel_ci_width = eval_ttest_significance(self.stats, p_threshold)
        stats["significance"] = significance
        stats["abs_ci_width"] = abs_ci_width
        stats["rel_ci_width"] = rel_ci_width
        for diff_type in ["abs", "rel"]:
            stats[f"ci_{diff_type}_diff"] = stats.apply(
                lambda x: (
                    x[f"{diff_type}_diff_mean"] - x[f"{diff_type}_ci_width"],
                    x[f"{diff_type}_diff_mean"] + x[f"{diff_type}_ci_width"],
                ),
                axis=1,
            )
            del stats[f"{diff_type}_ci_width"]
        return_cols = [col for col in stats.columns if col[-2:] != "_c"]
        return stats.loc[:, return_cols]

    def summary_barplot(
        self, p_threshold: float = 0.05, diff_type: str = "rel", display_ci: bool = True
    ) -> plotly.graph_objs.Figure:
        """plot impact and confidence interval for each metric

        Parameters
        ----------
        p_threshold : float, optional
            significance level, by default 0.05

        Returns
        -------
        plotly.graph_objs.Figure
        """
        if self.stats is None:
            raise ValueError("A/B test statistics haven't been calculated. Please call evaluate() in advance.")
        if diff_type not in ["rel", "abs"]:
            raise ValueError("Specified diff type is invalid.")

        stats = self.stats.copy(deep=True)
        significance, abs_ci_width, rel_ci_width = eval_ttest_significance(self.stats, p_threshold)
        stats["significant"] = significance
        stats["abs_ci_width"] = abs_ci_width
        stats["rel_ci_width"] = rel_ci_width

        viz_options = {
            "data_frame": stats.query(f"{self.variant_col} > 1"),  # not display control group
            "x": f"{diff_type}_diff_mean",
            "y": "metric",
            "facet_col": self.variant_col,
            "color": "significant",
            "color_discrete_map": {"up": "#54A24B", "down": "#E45756", "unclear": "silver"},
        }
        if display_ci:
            viz_options["error_x"] = f"{diff_type}_ci_width"

        g = px.bar(**viz_options)
        return g
