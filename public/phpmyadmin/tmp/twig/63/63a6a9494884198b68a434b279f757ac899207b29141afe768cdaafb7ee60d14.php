<?php

use Twig\Environment;
use Twig\Error\LoaderError;
use Twig\Error\RuntimeError;
use Twig\Extension\SandboxExtension;
use Twig\Markup;
use Twig\Sandbox\SecurityError;
use Twig\Sandbox\SecurityNotAllowedTagError;
use Twig\Sandbox\SecurityNotAllowedFilterError;
use Twig\Sandbox\SecurityNotAllowedFunctionError;
use Twig\Source;
use Twig\Template;

/* display/results/table.twig */
class __TwigTemplate_18b49433c2490cd26b8a4e3e65107c8b00d512862ace9e5782c5a8be3195156e extends \Twig\Template
{
    private $source;
    private $macros = [];

    public function __construct(Environment $env)
    {
        parent::__construct($env);

        $this->source = $this->getSourceContext();

        $this->parent = false;

        $this->blocks = [
        ];
    }

    protected function doDisplay(array $context, array $blocks = [])
    {
        $macros = $this->macros;
        // line 1
        ob_start(function () { return ''; });
        // line 2
        echo "  ";
        if ( !twig_test_empty(($context["navigation"] ?? null))) {
            // line 3
            echo "    <table class=\"pma-table navigation nospacing nopadding print_ignore\">
      <tr>
        <td class=\"navigation_separator\"></td>

        ";
            // line 7
            echo twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "move_backward_buttons", [], "any", false, false, false, 7);
            echo "
        ";
            // line 8
            echo twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "page_selector", [], "any", false, false, false, 8);
            echo "
        ";
            // line 9
            echo twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "move_forward_buttons", [], "any", false, false, false, 9);
            echo "

        ";
            // line 11
            if ((twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "number_total_page", [], "any", false, false, false, 11) > 1)) {
                // line 12
                echo "          <td><div class=\"navigation_separator\">|</div></td>
        ";
            }
            // line 14
            echo "
        ";
            // line 15
            if (twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "has_show_all", [], "any", false, false, false, 15)) {
                // line 16
                echo "          <td>
            <form action=\"";
                // line 17
                echo PhpMyAdmin\Url::getFromRoute("/sql");
                echo "\" method=\"post\">
              ";
                // line 18
                echo PhpMyAdmin\Url::getHiddenFields(twig_array_merge(twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "hidden_fields", [], "any", false, false, false, 18), ["session_max_rows" => twig_get_attribute($this->env, $this->source,                 // line 19
($context["navigation"] ?? null), "session_max_rows", [], "any", false, false, false, 19), "pos" => "0"]));
                // line 21
                echo "
              <input type=\"checkbox\" name=\"navig\" id=\"showAll_";
                // line 22
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\" class=\"showAllRows\" value=\"all\"";
                // line 23
                echo ((twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "is_showing_all", [], "any", false, false, false, 23)) ? (" checked") : (""));
                echo ">
              <label for=\"showAll_";
                // line 24
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\">";
                echo _gettext("Show all");
                echo "</label>
            </form>
          </td>
          <td><div class=\"navigation_separator\">|</div></td>
        ";
            }
            // line 29
            echo "
        <td>
          <div class=\"save_edited hide\">
            <input class=\"btn btn-link\" type=\"submit\" value=\"";
            // line 32
            echo _gettext("Save edited data");
            echo "\">
            <div class=\"navigation_separator\">|</div>
          </div>
        </td>
        <td>
          <div class=\"restore_column hide\">
            <input class=\"btn btn-link\" type=\"submit\" value=\"";
            // line 38
            echo _gettext("Restore column order");
            echo "\">
            <div class=\"navigation_separator\">|</div>
          </div>
        </td>
        <td class=\"navigation_goto\">
          <form action=\"";
            // line 43
            echo PhpMyAdmin\Url::getFromRoute("/sql");
            echo "\" method=\"post\" id=\"maxRowsForm\">
            ";
            // line 44
            echo PhpMyAdmin\Url::getHiddenFields(twig_array_merge(twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "hidden_fields", [], "any", false, false, false, 44), ["pos" => twig_get_attribute($this->env, $this->source,             // line 45
($context["navigation"] ?? null), "pos", [], "any", false, false, false, 45), "unlim_num_rows" =>             // line 46
($context["unlim_num_rows"] ?? null)]));
            // line 47
            echo "

            <label for=\"sessionMaxRowsSelect\">";
            // line 49
            echo _gettext("Number of rows:");
            echo "</label>
            <select class=\"autosubmit\" name=\"session_max_rows\" id=\"sessionMaxRowsSelect\">
              ";
            // line 51
            if (twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "is_showing_all", [], "any", false, false, false, 51)) {
                // line 52
                echo "                <option value=\"\" disabled selected>";
                echo _gettext("All");
                echo "</option>
              ";
            }
            // line 54
            echo "              ";
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable([0 => "25", 1 => "50", 2 => "100", 3 => "250", 4 => "500"]);
            foreach ($context['_seq'] as $context["_key"] => $context["option"]) {
                // line 55
                echo "                <option value=\"";
                echo twig_escape_filter($this->env, $context["option"], "html", null, true);
                echo "\"";
                echo (((twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "max_rows", [], "any", false, false, false, 55) == $context["option"])) ? (" selected") : (""));
                echo ">";
                echo twig_escape_filter($this->env, $context["option"], "html", null, true);
                echo "</option>
              ";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['option'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 57
            echo "            </select>
          </form>
        </td>
        <td class=\"navigation_separator\"></td>
        <td class=\"largescreenonly\">
          <span>";
            // line 62
            echo _gettext("Filter rows");
            echo ":</span>
          <input type=\"text\" class=\"filter_rows\" placeholder=\"";
            // line 64
            echo _gettext("Search this table");
            echo "\" data-for=\"";
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">
        </td>
        <td class=\"largescreenonly\">
          ";
            // line 67
            echo twig_get_attribute($this->env, $this->source, ($context["navigation"] ?? null), "sort_by_key", [], "any", false, false, false, 67);
            echo "
        </td>
        <td class=\"navigation_separator\"></td>
      </tr>
    </table>
  ";
        }
        $context["navigation_html"] = ('' === $tmp = ob_get_clean()) ? '' : new Markup($tmp, $this->env->getCharset());
        // line 74
        echo "
";
        // line 75
        echo ($context["sql_query_message"] ?? null);
        echo "

";
        // line 77
        echo twig_escape_filter($this->env, ($context["navigation_html"] ?? null), "html", null, true);
        echo "

<input class=\"save_cells_at_once\" type=\"hidden\" value=\"";
        // line 79
        echo twig_escape_filter($this->env, ($context["save_cells_at_once"] ?? null), "html", null, true);
        echo "\">
<div class=\"common_hidden_inputs\">
  ";
        // line 81
        echo PhpMyAdmin\Url::getHiddenInputs(($context["db"] ?? null), ($context["table"] ?? null));
        echo "
</div>

";
        // line 84
        if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 84))) {
            // line 85
            echo "  ";
            if (twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 85), "order", [], "any", false, false, false, 85)) {
                // line 86
                echo "    <input class=\"col_order\" type=\"hidden\" value=\"";
                echo twig_escape_filter($this->env, twig_join_filter(twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 86), "order", [], "any", false, false, false, 86), ","), "html", null, true);
                echo "\">
  ";
            }
            // line 88
            echo "  ";
            if (twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 88), "visibility", [], "any", false, false, false, 88)) {
                // line 89
                echo "    <input class=\"col_visib\" type=\"hidden\" value=\"";
                echo twig_escape_filter($this->env, twig_join_filter(twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 89), "visibility", [], "any", false, false, false, 89), ","), "html", null, true);
                echo "\">
  ";
            }
            // line 91
            echo "  ";
            if ( !twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 91), "is_view", [], "any", false, false, false, 91)) {
                // line 92
                echo "    <input class=\"table_create_time\" type=\"hidden\" value=\"";
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_order", [], "any", false, false, false, 92), "table_create_time", [], "any", false, false, false, 92), "html", null, true);
                echo "\">
  ";
            }
        }
        // line 95
        echo "
";
        // line 96
        if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 96))) {
            // line 97
            echo "  <form method=\"post\" action=\"";
            echo PhpMyAdmin\Url::getFromRoute("/sql");
            echo "\" name=\"displayOptionsForm\" class=\"ajax print_ignore\">
    ";
            // line 98
            echo PhpMyAdmin\Url::getHiddenInputs(["db" =>             // line 99
($context["db"] ?? null), "table" =>             // line 100
($context["table"] ?? null), "sql_query" =>             // line 101
($context["sql_query"] ?? null), "goto" =>             // line 102
($context["goto"] ?? null), "display_options_form" => 1]);
            // line 104
            echo "

    <div";
            // line 106
            if ((($context["default_sliders_state"] ?? null) != "disabled")) {
                // line 107
                echo (((($context["default_sliders_state"] ?? null) == "closed")) ? (" style=\"display: none; overflow:auto;\"") : (""));
                echo " class=\"pma_auto_slider\" title=\"";
                echo _gettext("Options");
                echo "\"";
            }
            // line 108
            echo ">

      <fieldset>
        <div class=\"formelement\">
          <div>
            <input type=\"radio\" name=\"pftext\" id=\"partialFulltextRadioP";
            // line 113
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\" value=\"P\"";
            echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 113), "pftext", [], "any", false, false, false, 113) == "P")) ? (" checked") : (""));
            echo ">
            <label for=\"partialFulltextRadioP";
            // line 114
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Partial texts");
            echo "</label>
          </div>
          <div>
            <input type=\"radio\" name=\"pftext\" id=\"partialFulltextRadioF";
            // line 117
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\" value=\"F\"";
            echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 117), "pftext", [], "any", false, false, false, 117) == "F")) ? (" checked") : (""));
            echo ">
            <label for=\"partialFulltextRadioF";
            // line 118
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Full texts");
            echo "</label>
          </div>
        </div>

        ";
            // line 122
            if ((($context["relwork"] ?? null) && ($context["displaywork"] ?? null))) {
                // line 123
                echo "          <div class=\"formelement\">
            <div>
              <input type=\"radio\" name=\"relational_display\" id=\"relationalDisplayRadioK";
                // line 125
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\" value=\"K\"";
                echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 125), "relational_display", [], "any", false, false, false, 125) == "K")) ? (" checked") : (""));
                echo ">
              <label for=\"relationalDisplayRadioK";
                // line 126
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\">";
                echo _gettext("Relational key");
                echo "</label>
            </div>
            <div>
              <input type=\"radio\" name=\"relational_display\" id=\"relationalDisplayRadioD";
                // line 129
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\" value=\"D\"";
                echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 129), "relational_display", [], "any", false, false, false, 129) == "D")) ? (" checked") : (""));
                echo ">
              <label for=\"relationalDisplayRadioD";
                // line 130
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\">";
                echo _gettext("Display column for relationships");
                echo "</label>
            </div>
          </div>
        ";
            }
            // line 134
            echo "
        <div class=\"formelement\">
          <input type=\"checkbox\" name=\"display_binary\" id=\"display_binary_";
            // line 136
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\"";
            // line 137
            echo (( !twig_test_empty(twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 137), "display_binary", [], "any", false, false, false, 137))) ? (" checked") : (""));
            echo ">
          <label for=\"display_binary_";
            // line 138
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Show binary contents");
            echo "</label>

          <input type=\"checkbox\" name=\"display_blob\" id=\"display_blob_";
            // line 140
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\"";
            // line 141
            echo (( !twig_test_empty(twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 141), "display_blob", [], "any", false, false, false, 141))) ? (" checked") : (""));
            echo ">
          <label for=\"display_blob_";
            // line 142
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Show BLOB contents");
            echo "</label>
        </div>

        ";
            // line 149
            echo "        <div class=\"formelement\">
          <input type=\"checkbox\" name=\"hide_transformation\" id=\"hide_transformation_";
            // line 150
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\"";
            // line 151
            echo (( !twig_test_empty(twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 151), "hide_transformation", [], "any", false, false, false, 151))) ? (" checked") : (""));
            echo ">
          <label for=\"hide_transformation_";
            // line 152
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Hide browser transformation");
            echo "</label>
        </div>

        <div class=\"formelement\">
          ";
            // line 156
            if (twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 156), "possible_as_geometry", [], "any", false, false, false, 156)) {
                // line 157
                echo "            <div>
              <input type=\"radio\" name=\"geoOption\" id=\"geoOptionRadioGeom";
                // line 158
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\" value=\"GEOM\"";
                echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 158), "geo_option", [], "any", false, false, false, 158) == "GEOM")) ? (" checked") : (""));
                echo ">
              <label for=\"geoOptionRadioGeom";
                // line 159
                echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
                echo "\">";
                echo _gettext("Geometry");
                echo "</label>
            </div>
          ";
            }
            // line 162
            echo "          <div>
            <input type=\"radio\" name=\"geoOption\" id=\"geoOptionRadioWkt";
            // line 163
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\" value=\"WKT\"";
            echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 163), "geo_option", [], "any", false, false, false, 163) == "WKT")) ? (" checked") : (""));
            echo ">
            <label for=\"geoOptionRadioWkt";
            // line 164
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Well Known Text");
            echo "</label>
          </div>
          <div>
            <input type=\"radio\" name=\"geoOption\" id=\"geoOptionRadioWkb";
            // line 167
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\" value=\"WKB\"";
            echo (((twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "options", [], "any", false, false, false, 167), "geo_option", [], "any", false, false, false, 167) == "WKB")) ? (" checked") : (""));
            echo ">
            <label for=\"geoOptionRadioWkb";
            // line 168
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\">";
            echo _gettext("Well Known Binary");
            echo "</label>
          </div>
        </div>
        <div class=\"clearfloat\"></div>
      </fieldset>

      <fieldset class=\"tblFooters\">
        <input class=\"btn btn-primary\" type=\"submit\" value=\"";
            // line 175
            echo _gettext("Go");
            echo "\">
      </fieldset>
    </div>
  </form>
";
        }
        // line 180
        echo "
";
        // line 181
        if (twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "has_bulk_actions_form", [], "any", false, false, false, 181)) {
            // line 182
            echo "  <form method=\"post\" name=\"resultsForm\" id=\"resultsForm_";
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "\" class=\"ajax\">
    ";
            // line 183
            echo PhpMyAdmin\Url::getHiddenInputs(($context["db"] ?? null), ($context["table"] ?? null), 1);
            echo "
    <input type=\"hidden\" name=\"goto\" value=\"";
            // line 184
            echo PhpMyAdmin\Url::getFromRoute("/sql");
            echo "\">
";
        }
        // line 186
        echo "
  <div class=\"table-responsive-md\">
    <table class=\"table table-light table-striped table-hover table-sm table_results data ajax w-auto\" data-uniqueId=\"";
        // line 188
        echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
        echo "\">

      ";
        // line 190
        echo twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "button", [], "any", false, false, false, 190);
        echo "
      ";
        // line 191
        echo twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "table_headers_for_columns", [], "any", false, false, false, 191);
        echo "
      ";
        // line 192
        echo twig_get_attribute($this->env, $this->source, ($context["headers"] ?? null), "column_at_right_side", [], "any", false, false, false, 192);
        echo "

        </tr>
      </thead>

      <tbody>
        ";
        // line 198
        echo ($context["body"] ?? null);
        echo "
      </tbody>
    </table>
  </div>

";
        // line 203
        if ( !twig_test_empty(($context["bulk_links"] ?? null))) {
            // line 204
            echo "    <div class=\"print_ignore\">
      <img class=\"selectallarrow\" src=\"";
            // line 205
            echo twig_escape_filter($this->env, ($context["select_all_arrow"] ?? null), "html", null, true);
            echo "\" width=\"38\" height=\"22\" alt=\"";
            echo _gettext("With selected:");
            echo "\">
      <input type=\"checkbox\" id=\"resultsForm_";
            // line 206
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "_checkall\" class=\"checkall_box\" title=\"";
            echo _gettext("Check all");
            echo "\">
      <label for=\"resultsForm_";
            // line 207
            echo twig_escape_filter($this->env, ($context["unique_id"] ?? null), "html", null, true);
            echo "_checkall\">";
            echo _gettext("Check all");
            echo "</label>
      <em class=\"with-selected\">";
            // line 208
            echo _gettext("With selected:");
            echo "</em>

      <button class=\"btn btn-link mult_submit\" type=\"submit\" name=\"submit_mult\" value=\"edit\" title=\"";
            // line 210
            echo _gettext("Edit");
            echo "\">
        ";
            // line 211
            echo \PhpMyAdmin\Html\Generator::getIcon("b_edit", _gettext("Edit"));
            echo "
      </button>

      <button class=\"btn btn-link mult_submit\" type=\"submit\" name=\"submit_mult\" value=\"copy\" title=\"";
            // line 214
            echo _gettext("Copy");
            echo "\">
        ";
            // line 215
            echo \PhpMyAdmin\Html\Generator::getIcon("b_insrow", _gettext("Copy"));
            echo "
      </button>

      <button class=\"btn btn-link mult_submit\" type=\"submit\" name=\"submit_mult\" value=\"delete\" title=\"";
            // line 218
            echo _gettext("Delete");
            echo "\">
        ";
            // line 219
            echo \PhpMyAdmin\Html\Generator::getIcon("b_drop", _gettext("Delete"));
            echo "
      </button>

      ";
            // line 222
            if (twig_get_attribute($this->env, $this->source, ($context["bulk_links"] ?? null), "has_export_button", [], "any", false, false, false, 222)) {
                // line 223
                echo "        <button class=\"btn btn-link mult_submit\" type=\"submit\" name=\"submit_mult\" value=\"export\" title=\"";
                echo _gettext("Export");
                echo "\">
          ";
                // line 224
                echo \PhpMyAdmin\Html\Generator::getIcon("b_tblexport", _gettext("Export"));
                echo "
        </button>
      ";
            }
            // line 227
            echo "    </div>

    <input type=\"hidden\" name=\"clause_is_unique\" value=\"";
            // line 229
            echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["bulk_links"] ?? null), "clause_is_unique", [], "any", false, false, false, 229), "html", null, true);
            echo "\">
    <input type=\"hidden\" name=\"sql_query\" value=\"";
            // line 230
            echo twig_escape_filter($this->env, ($context["sql_query"] ?? null), "html", null, true);
            echo "\">
  </form>
";
        }
        // line 233
        echo "
";
        // line 234
        echo twig_escape_filter($this->env, ($context["navigation_html"] ?? null), "html", null, true);
        echo "

";
        // line 236
        if ( !twig_test_empty(($context["operations"] ?? null))) {
            // line 237
            echo "  <fieldset class=\"print_ignore\">
    <legend>";
            // line 238
            echo _gettext("Query results operations");
            echo "</legend>

    ";
            // line 240
            if (twig_get_attribute($this->env, $this->source, ($context["operations"] ?? null), "has_print_link", [], "any", false, false, false, 240)) {
                // line 241
                echo "      ";
                echo PhpMyAdmin\Html\Generator::linkOrButton("#", null, \PhpMyAdmin\Html\Generator::getIcon("b_print", _gettext("Print"), true), ["id" => "printView", "class" => "btn"], "print_view");
                // line 247
                echo "

      ";
                // line 249
                echo PhpMyAdmin\Html\Generator::linkOrButton("#", null, \PhpMyAdmin\Html\Generator::getIcon("b_insrow", _gettext("Copy to clipboard"), true), ["id" => "copyToClipBoard", "class" => "btn"]);
                // line 254
                echo "
    ";
            }
            // line 256
            echo "
    ";
            // line 257
            if ( !twig_get_attribute($this->env, $this->source, ($context["operations"] ?? null), "has_procedure", [], "any", false, false, false, 257)) {
                // line 258
                echo "      ";
                if (twig_get_attribute($this->env, $this->source, ($context["operations"] ?? null), "has_export_link", [], "any", false, false, false, 258)) {
                    // line 259
                    echo "        ";
                    echo PhpMyAdmin\Html\Generator::linkOrButton(PhpMyAdmin\Url::getFromRoute("/table/export"), twig_get_attribute($this->env, $this->source,                     // line 261
($context["operations"] ?? null), "url_params", [], "any", false, false, false, 261), \PhpMyAdmin\Html\Generator::getIcon("b_tblexport", _gettext("Export"), true), ["class" => "btn"]);
                    // line 264
                    echo "

        ";
                    // line 266
                    echo PhpMyAdmin\Html\Generator::linkOrButton(PhpMyAdmin\Url::getFromRoute("/table/chart"), twig_get_attribute($this->env, $this->source,                     // line 268
($context["operations"] ?? null), "url_params", [], "any", false, false, false, 268), \PhpMyAdmin\Html\Generator::getIcon("b_chart", _gettext("Display chart"), true), ["class" => "btn"]);
                    // line 271
                    echo "

        ";
                    // line 273
                    if (twig_get_attribute($this->env, $this->source, ($context["operations"] ?? null), "has_geometry", [], "any", false, false, false, 273)) {
                        // line 274
                        echo "          ";
                        echo PhpMyAdmin\Html\Generator::linkOrButton(PhpMyAdmin\Url::getFromRoute("/table/gis-visualization"), twig_get_attribute($this->env, $this->source,                         // line 276
($context["operations"] ?? null), "url_params", [], "any", false, false, false, 276), \PhpMyAdmin\Html\Generator::getIcon("b_globe", _gettext("Visualize GIS data"), true), ["class" => "btn"]);
                        // line 279
                        echo "
        ";
                    }
                    // line 281
                    echo "      ";
                }
                // line 282
                echo "
      <span>
        ";
                // line 284
                echo PhpMyAdmin\Html\Generator::linkOrButton(PhpMyAdmin\Url::getFromRoute("/view/create"), ["db" =>                 // line 286
($context["db"] ?? null), "table" => ($context["table"] ?? null), "sql_query" => ($context["sql_query"] ?? null), "printview" => true], \PhpMyAdmin\Html\Generator::getIcon("b_view_add", _gettext("Create view"), true), ["class" => "btn create_view ajax"]);
                // line 289
                echo "
      </span>
    ";
            }
            // line 292
            echo "  </fieldset>
";
        }
    }

    public function getTemplateName()
    {
        return "display/results/table.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  682 => 292,  677 => 289,  675 => 286,  674 => 284,  670 => 282,  667 => 281,  663 => 279,  661 => 276,  659 => 274,  657 => 273,  653 => 271,  651 => 268,  650 => 266,  646 => 264,  644 => 261,  642 => 259,  639 => 258,  637 => 257,  634 => 256,  630 => 254,  628 => 249,  624 => 247,  621 => 241,  619 => 240,  614 => 238,  611 => 237,  609 => 236,  604 => 234,  601 => 233,  595 => 230,  591 => 229,  587 => 227,  581 => 224,  576 => 223,  574 => 222,  568 => 219,  564 => 218,  558 => 215,  554 => 214,  548 => 211,  544 => 210,  539 => 208,  533 => 207,  527 => 206,  521 => 205,  518 => 204,  516 => 203,  508 => 198,  499 => 192,  495 => 191,  491 => 190,  486 => 188,  482 => 186,  477 => 184,  473 => 183,  468 => 182,  466 => 181,  463 => 180,  455 => 175,  443 => 168,  437 => 167,  429 => 164,  423 => 163,  420 => 162,  412 => 159,  406 => 158,  403 => 157,  401 => 156,  392 => 152,  388 => 151,  385 => 150,  382 => 149,  374 => 142,  370 => 141,  367 => 140,  360 => 138,  356 => 137,  353 => 136,  349 => 134,  340 => 130,  334 => 129,  326 => 126,  320 => 125,  316 => 123,  314 => 122,  305 => 118,  299 => 117,  291 => 114,  285 => 113,  278 => 108,  272 => 107,  270 => 106,  266 => 104,  264 => 102,  263 => 101,  262 => 100,  261 => 99,  260 => 98,  255 => 97,  253 => 96,  250 => 95,  243 => 92,  240 => 91,  234 => 89,  231 => 88,  225 => 86,  222 => 85,  220 => 84,  214 => 81,  209 => 79,  204 => 77,  199 => 75,  196 => 74,  186 => 67,  178 => 64,  174 => 62,  167 => 57,  154 => 55,  149 => 54,  143 => 52,  141 => 51,  136 => 49,  132 => 47,  130 => 46,  129 => 45,  128 => 44,  124 => 43,  116 => 38,  107 => 32,  102 => 29,  92 => 24,  88 => 23,  85 => 22,  82 => 21,  80 => 19,  79 => 18,  75 => 17,  72 => 16,  70 => 15,  67 => 14,  63 => 12,  61 => 11,  56 => 9,  52 => 8,  48 => 7,  42 => 3,  39 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "display/results/table.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/display/results/table.twig");
    }
}
