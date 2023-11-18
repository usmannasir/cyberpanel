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

/* export.twig */
class __TwigTemplate_9c4626f6172aaee2e8edb1d97c096b7553d2d83757b3af2e2a90e214ad2dd56d extends \Twig\Template
{
    private $source;
    private $macros = [];

    public function __construct(Environment $env)
    {
        parent::__construct($env);

        $this->source = $this->getSourceContext();

        $this->parent = false;

        $this->blocks = [
            'message' => [$this, 'block_message'],
            'title' => [$this, 'block_title'],
            'selection_options' => [$this, 'block_selection_options'],
        ];
    }

    protected function doDisplay(array $context, array $blocks = [])
    {
        $macros = $this->macros;
        // line 1
        echo ($context["page_settings_error_html"] ?? null);
        echo "
";
        // line 2
        echo ($context["page_settings_html"] ?? null);
        echo "

";
        // line 4
        $this->displayBlock('message', $context, $blocks);
        // line 5
        echo "
<div class=\"exportoptions row\" id=\"header\">
  <h2>
    ";
        // line 8
        echo \PhpMyAdmin\Html\Generator::getImage("b_export", _gettext("Export"));
        echo "
    ";
        // line 9
        $this->displayBlock('title', $context, $blocks);
        // line 10
        echo "  </h2>
</div>

";
        // line 13
        if (twig_get_attribute($this->env, $this->source, ($context["templates"] ?? null), "is_enabled", [], "any", false, false, false, 13)) {
            // line 14
            echo "  <div class=\"exportoptions\" id=\"export_templates\">
    <h3>";
            // line 15
            echo _gettext("Export templates:");
            echo "</h3>

    <div class=\"floatleft\">
      <form method=\"post\" action=\"";
            // line 18
            echo PhpMyAdmin\Url::getFromRoute("/export/template/create");
            echo "\" id=\"newTemplateForm\" class=\"ajax\">
        <h4>";
            // line 19
            echo _gettext("New template:");
            echo "</h4>
        <input type=\"text\" name=\"templateName\" id=\"templateName\" maxlength=\"64\" placeholder=\"";
            // line 20
            echo _gettext("Template name");
            echo "\" required>
        <input class=\"btn btn-secondary\" type=\"submit\" name=\"createTemplate\" id=\"createTemplate\" value=\"";
            // line 21
            echo _gettext("Create");
            echo "\">
      </form>
    </div>

    <div class=\"floatleft\" style=\"margin-left: 50px;\">
      <form method=\"post\" id=\"existingTemplatesForm\" class=\"ajax\">
        <h4>";
            // line 27
            echo _gettext("Existing templates:");
            echo "</h4>
        <label for=\"template\">";
            // line 28
            echo _gettext("Template:");
            echo "</label>
        <select name=\"template\" id=\"template\" required>
          <option value=\"\">-- ";
            // line 30
            echo _gettext("Select a template");
            echo " --</option>
          ";
            // line 31
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable(twig_get_attribute($this->env, $this->source, ($context["templates"] ?? null), "templates", [], "any", false, false, false, 31));
            foreach ($context['_seq'] as $context["_key"] => $context["template"]) {
                // line 32
                echo "            <option value=\"";
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, $context["template"], "getId", [], "method", false, false, false, 32), "html", null, true);
                echo "\"";
                echo (((twig_get_attribute($this->env, $this->source, $context["template"], "getId", [], "method", false, false, false, 32) == twig_get_attribute($this->env, $this->source, ($context["templates"] ?? null), "selected", [], "any", false, false, false, 32))) ? (" selected") : (""));
                echo ">
              ";
                // line 33
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, $context["template"], "getName", [], "method", false, false, false, 33), "html", null, true);
                echo "
            </option>
          ";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['template'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 36
            echo "        </select>
        <input class=\"btn btn-secondary\" type=\"submit\" formaction=\"";
            // line 37
            echo PhpMyAdmin\Url::getFromRoute("/export/template/update");
            echo "\" name=\"updateTemplate\" id=\"updateTemplate\" value=\"";
            echo _gettext("Update");
            echo "\">
        <input class=\"btn btn-secondary\" type=\"submit\" formaction=\"";
            // line 38
            echo PhpMyAdmin\Url::getFromRoute("/export/template/delete");
            echo "\" name=\"deleteTemplate\" id=\"deleteTemplate\" value=\"";
            echo _gettext("Delete");
            echo "\">
      </form>
    </div>

    <div class=\"clearfloat\"></div>
  </div>
";
        }
        // line 45
        echo "
";
        // line 46
        if ( !twig_test_empty(($context["sql_query"] ?? null))) {
            // line 47
            echo "  <div class=\"exportoptions\">
    ";
            // line 49
            echo "    <h3>";
            echo _gettext("SQL query:");
            echo "</h3>
    <div class=\"floatleft\">
      <div id=\"sqlqueryform\">
        ";
            // line 53
            echo "        <input class=\"btn btn-secondary\" type=\"submit\" id=\"showsqlquery\" value=\"";
            echo _gettext("Show SQL query");
            echo "\">
      </div>
      <div class=\"d-none\">
        <div id=\"export_sql_modal_content\">
          <code class=\"sql\">
            <pre id=\"sql_preview_query\">";
            // line 58
            echo twig_escape_filter($this->env, ($context["sql_query"] ?? null), "html", null, true);
            echo "</pre>
          </code>
        </div>
      </div>
    </div>
    <div class=\"clearfloat\"></div>
  </div>
";
        }
        // line 66
        echo "
<form method=\"post\" action=\"";
        // line 67
        echo PhpMyAdmin\Url::getFromRoute("/export");
        echo "\" name=\"dump\" class=\"disableAjax\">
  ";
        // line 68
        echo PhpMyAdmin\Url::getHiddenInputs(($context["hidden_inputs"] ?? null));
        echo "

  ";
        // line 70
        if ((($context["export_method"] ?? null) != "custom-no-form")) {
            // line 71
            echo "    <div class=\"exportoptions\" id=\"quick_or_custom\">
      <h3>";
            // line 72
            echo _gettext("Export method:");
            echo "</h3>
      <ul>
        <li>
          <input type=\"radio\" name=\"quick_or_custom\" value=\"quick\" id=\"radio_quick_export\"";
            // line 76
            echo (((($context["export_method"] ?? null) == "quick")) ? (" checked") : (""));
            echo ">
          <label for=\"radio_quick_export\">
            ";
            // line 78
            echo _gettext("Quick - display only the minimal options");
            // line 79
            echo "          </label>
        </li>

        <li>
          <input type=\"radio\" name=\"quick_or_custom\" value=\"custom\" id=\"radio_custom_export\"";
            // line 84
            echo (((($context["export_method"] ?? null) == "custom")) ? (" checked") : (""));
            echo ">
          <label for=\"radio_custom_export\">
            ";
            // line 86
            echo _gettext("Custom - display all possible options");
            // line 87
            echo "          </label>
        </li>
      </ul>
    </div>
  ";
        }
        // line 92
        echo "
  <div class=\"exportoptions\" id=\"format\">
    <h3>";
        // line 94
        echo _gettext("Format:");
        echo "</h3>
    ";
        // line 95
        echo ($context["dropdown"] ?? null);
        echo "
  </div>

  ";
        // line 98
        $this->displayBlock('selection_options', $context, $blocks);
        // line 99
        echo "
  ";
        // line 100
        if ( !twig_test_empty(($context["rows"] ?? null))) {
            // line 101
            echo "    <div class=\"exportoptions\" id=\"rows\">
      <h3>";
            // line 102
            echo _gettext("Rows:");
            echo "</h3>
      <ul>
        <li>
          <input type=\"radio\" name=\"allrows\" value=\"0\" id=\"radio_allrows_0\"";
            // line 106
            echo ((( !(null === twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "allrows", [], "any", false, false, false, 106)) && (twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "allrows", [], "any", false, false, false, 106) == 0))) ? (" checked") : (""));
            echo ">
          <label for=\"radio_allrows_0\">";
            // line 107
            echo _gettext("Dump some row(s)");
            echo "</label>
          <ul>
            <li>
              <label for=\"limit_to\">";
            // line 110
            echo _gettext("Number of rows:");
            echo "</label>
              <input type=\"text\" id=\"limit_to\" name=\"limit_to\" size=\"5\" value=\"";
            // line 112
            if ( !(null === twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "limit_to", [], "any", false, false, false, 112))) {
                // line 113
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "limit_to", [], "any", false, false, false, 113), "html", null, true);
            } elseif (( !twig_test_empty(twig_get_attribute($this->env, $this->source,             // line 114
($context["rows"] ?? null), "unlim_num_rows", [], "any", false, false, false, 114)) && (twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "unlim_num_rows", [], "any", false, false, false, 114) != 0))) {
                // line 115
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "unlim_num_rows", [], "any", false, false, false, 115), "html", null, true);
            } else {
                // line 117
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "number_of_rows", [], "any", false, false, false, 117), "html", null, true);
            }
            // line 118
            echo "\" onfocus=\"this.select()\">
            </li>
            <li>
              <label for=\"limit_from\">";
            // line 121
            echo _gettext("Row to begin at:");
            echo "</label>
              <input type=\"text\" id=\"limit_from\" name=\"limit_from\" size=\"5\" value=\"";
            // line 123
            (( !(null === twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "limit_from", [], "any", false, false, false, 123))) ? (print (twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "limit_from", [], "any", false, false, false, 123), "html", null, true))) : (print (0)));
            echo "\" onfocus=\"this.select()\">
            </li>
          </ul>
        </li>
        <li>
          <input type=\"radio\" name=\"allrows\" value=\"1\" id=\"radio_allrows_1\"";
            // line 129
            echo ((((null === twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "allrows", [], "any", false, false, false, 129)) || (twig_get_attribute($this->env, $this->source, ($context["rows"] ?? null), "allrows", [], "any", false, false, false, 129) == 1))) ? (" checked") : (""));
            echo ">
          <label for=\"radio_allrows_1\">";
            // line 130
            echo _gettext("Dump all rows");
            echo "</label>
        </li>
      </ul>
    </div>
  ";
        }
        // line 135
        echo "
  ";
        // line 136
        if (($context["has_save_dir"] ?? null)) {
            // line 137
            echo "    <div class=\"exportoptions\" id=\"output_quick_export\">
      <h3>";
            // line 138
            echo _gettext("Output:");
            echo "</h3>
      <ul>
        <li>
          <input type=\"checkbox\" name=\"quick_export_onserver\" value=\"saveit\" id=\"checkbox_quick_dump_onserver\"";
            // line 141
            echo ((($context["export_is_checked"] ?? null)) ? (" checked") : (""));
            echo ">
          <label for=\"checkbox_quick_dump_onserver\">
            ";
            // line 143
            echo twig_sprintf(_gettext("Save on server in the directory <strong>%s</strong>"), twig_escape_filter($this->env, ($context["save_dir"] ?? null)));
            echo "
          </label>
        </li>
        <li>
          <input type=\"checkbox\" name=\"quick_export_onserver_overwrite\" value=\"saveitover\" id=\"checkbox_quick_dump_onserver_overwrite\"";
            // line 148
            echo ((($context["export_overwrite_is_checked"] ?? null)) ? (" checked") : (""));
            echo ">
          <label for=\"checkbox_quick_dump_onserver_overwrite\">
            ";
            // line 150
            echo _gettext("Overwrite existing file(s)");
            // line 151
            echo "          </label>
        </li>
      </ul>
    </div>
  ";
        }
        // line 156
        echo "
  <div id=\"alias_modal\" class=\"hide\" title=\"";
        // line 157
        echo _gettext("Rename exported databases/tables/columns");
        echo "\">
    <table class=\"pma-table\" id=\"alias_data\">
      <thead>
      <tr>
        <th colspan=\"4\">
          ";
        // line 162
        echo _gettext("Defined aliases");
        // line 163
        echo "        </th>
      </tr>
      </thead>

      <tbody>
      ";
        // line 168
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["aliases"] ?? null));
        foreach ($context['_seq'] as $context["db"] => $context["db_data"]) {
            // line 169
            echo "        ";
            if ((twig_get_attribute($this->env, $this->source, $context["db_data"], "alias", [], "any", true, true, false, 169) &&  !(null === twig_get_attribute($this->env, $this->source, $context["db_data"], "alias", [], "any", false, false, false, 169)))) {
                // line 170
                echo "          <tr>
            <th>";
                // line 171
                echo _pgettext(                "Alias", "Database");
                echo "</th>
            <td>";
                // line 172
                echo twig_escape_filter($this->env, $context["db"], "html", null, true);
                echo "</td>
            <td>
              <input name=\"aliases[";
                // line 174
                echo twig_escape_filter($this->env, $context["db"], "html", null, true);
                echo "][alias]\" value=\"";
                echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, $context["db_data"], "alias", [], "any", false, false, false, 174), "html", null, true);
                echo "\" type=\"text\">
            </td>
            <td>
              <button class=\"alias_remove btn btn-secondary\">";
                // line 177
                echo _gettext("Remove");
                echo "</button>
            </td>
          </tr>
        ";
            }
            // line 181
            echo "
        ";
            // line 182
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable((((twig_get_attribute($this->env, $this->source, $context["db_data"], "tables", [], "any", true, true, false, 182) &&  !(null === twig_get_attribute($this->env, $this->source, $context["db_data"], "tables", [], "any", false, false, false, 182)))) ? (twig_get_attribute($this->env, $this->source, $context["db_data"], "tables", [], "any", false, false, false, 182)) : ([])));
            foreach ($context['_seq'] as $context["table"] => $context["table_data"]) {
                // line 183
                echo "          ";
                if ((twig_get_attribute($this->env, $this->source, $context["table_data"], "alias", [], "any", true, true, false, 183) &&  !(null === twig_get_attribute($this->env, $this->source, $context["table_data"], "alias", [], "any", false, false, false, 183)))) {
                    // line 184
                    echo "            <tr>
              <th>";
                    // line 185
                    echo _pgettext(                    "Alias", "Table");
                    echo "</th>
              <td>";
                    // line 186
                    echo twig_escape_filter($this->env, $context["db"], "html", null, true);
                    echo ".";
                    echo twig_escape_filter($this->env, $context["table"], "html", null, true);
                    echo "</td>
              <td>
                <input name=\"aliases[";
                    // line 188
                    echo twig_escape_filter($this->env, $context["db"], "html", null, true);
                    echo "][tables][";
                    echo twig_escape_filter($this->env, $context["table"], "html", null, true);
                    echo "][alias]\" value=\"";
                    echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, $context["table_data"], "alias", [], "any", false, false, false, 188), "html", null, true);
                    echo "\" type=\"text\">
              </td>
              <td>
                <button class=\"alias_remove btn btn-secondary\">";
                    // line 191
                    echo _gettext("Remove");
                    echo "</button>
              </td>
            </tr>
          ";
                }
                // line 195
                echo "
          ";
                // line 196
                $context['_parent'] = $context;
                $context['_seq'] = twig_ensure_traversable((((twig_get_attribute($this->env, $this->source, $context["table_data"], "columns", [], "any", true, true, false, 196) &&  !(null === twig_get_attribute($this->env, $this->source, $context["table_data"], "columns", [], "any", false, false, false, 196)))) ? (twig_get_attribute($this->env, $this->source, $context["table_data"], "columns", [], "any", false, false, false, 196)) : ([])));
                foreach ($context['_seq'] as $context["column"] => $context["column_name"]) {
                    // line 197
                    echo "            <tr>
              <th>";
                    // line 198
                    echo _pgettext(                    "Alias", "Column");
                    echo "</th>
              <td>";
                    // line 199
                    echo twig_escape_filter($this->env, $context["db"], "html", null, true);
                    echo ".";
                    echo twig_escape_filter($this->env, $context["table"], "html", null, true);
                    echo ".";
                    echo twig_escape_filter($this->env, $context["column"], "html", null, true);
                    echo "</td>
              <td>
                <input name=\"aliases[";
                    // line 201
                    echo twig_escape_filter($this->env, $context["db"], "html", null, true);
                    echo "][tables][";
                    echo twig_escape_filter($this->env, $context["table"], "html", null, true);
                    echo "][colums][";
                    echo twig_escape_filter($this->env, $context["column"], "html", null, true);
                    echo "]\" value=\"";
                    echo twig_escape_filter($this->env, $context["column_name"], "html", null, true);
                    echo "\" type=\"text\">
              </td>
              <td>
                <button class=\"alias_remove btn btn-secondary\">";
                    // line 204
                    echo _gettext("Remove");
                    echo "</button>
              </td>
            </tr>
          ";
                }
                $_parent = $context['_parent'];
                unset($context['_seq'], $context['_iterated'], $context['column'], $context['column_name'], $context['_parent'], $context['loop']);
                $context = array_intersect_key($context, $_parent) + $_parent;
                // line 208
                echo "        ";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['table'], $context['table_data'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 209
            echo "      ";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['db'], $context['db_data'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 210
        echo "      </tbody>

      ";
        // line 213
        echo "      <tfoot class=\"hide\">
      <tr>
        <th></th>
        <td></td>
        <td>
          <input name=\"aliases_new\" value=\"\" type=\"text\">
        </td>
        <td>
          <button class=\"alias_remove btn btn-secondary\">";
        // line 221
        echo _gettext("Remove");
        echo "</button>
        </td>
      </tr>
      </tfoot>
    </table>

    <table class=\"pma-table\">
      <thead>
      <tr>
        <th colspan=\"4\">";
        // line 230
        echo _gettext("Define new aliases");
        echo "</th>
      </tr>
      </thead>
      <tr>
        <td>
          <label>";
        // line 235
        echo _gettext("Select database:");
        echo "</label>
        </td>
        <td>
          <select id=\"db_alias_select\"><option value=\"\"></option></select>
        </td>
        <td>
          <input id=\"db_alias_name\" placeholder=\"";
        // line 241
        echo _gettext("New database name");
        echo "\" disabled=\"1\">
        </td>
        <td>
          <button id=\"db_alias_button\" class=\"btn btn-secondary\" disabled=\"1\">";
        // line 244
        echo _gettext("Add");
        echo "</button>
        </td>
      </tr>
      <tr>
        <td>
          <label>";
        // line 249
        echo _gettext("Select table:");
        echo "</label>
        </td>
        <td>
          <select id=\"table_alias_select\"><option value=\"\"></option></select>
        </td>
        <td>
          <input id=\"table_alias_name\" placeholder=\"";
        // line 255
        echo _gettext("New table name");
        echo "\" disabled=\"1\">
        </td>
        <td>
          <button id=\"table_alias_button\" class=\"btn btn-secondary\" disabled=\"1\">";
        // line 258
        echo _gettext("Add");
        echo "</button>
        </td>
      </tr>
      <tr>
        <td>
          <label>";
        // line 263
        echo _gettext("Select column:");
        echo "</label>
        </td>
        <td>
          <select id=\"column_alias_select\"><option value=\"\"></option></select>
        </td>
        <td>
          <input id=\"column_alias_name\" placeholder=\"";
        // line 269
        echo _gettext("New column name");
        echo "\" disabled=\"1\">
        </td>
        <td>
          <button id=\"column_alias_button\" class=\"btn btn-secondary\" disabled=\"1\">";
        // line 272
        echo _gettext("Add");
        echo "</button>
        </td>
      </tr>
    </table>
  </div>

  <div class=\"exportoptions\" id=\"output\">
    <h3>";
        // line 279
        echo _gettext("Output:");
        echo "</h3>
    <ul id=\"ul_output\">
      <li>
        <input type=\"checkbox\" id=\"btn_alias_config\"";
        // line 282
        echo ((($context["has_aliases"] ?? null)) ? (" checked") : (""));
        echo ">
        <label for=\"btn_alias_config\">
          ";
        // line 284
        echo _gettext("Rename exported databases/tables/columns");
        // line 285
        echo "        </label>
      </li>

      ";
        // line 288
        if ((($context["export_type"] ?? null) != "server")) {
            // line 289
            echo "        <li>
          <input type=\"checkbox\" name=\"lock_tables\" value=\"something\" id=\"checkbox_lock_tables\"";
            // line 291
            echo (((( !($context["repopulate"] ?? null) && ($context["is_checked_lock_tables"] ?? null)) || ($context["lock_tables"] ?? null))) ? (" checked") : (""));
            echo ">
          <label for=\"checkbox_lock_tables\">
            ";
            // line 293
            echo twig_sprintf(_gettext("Use %s statement"), "<code>LOCK TABLES</code>");
            echo "
          </label>
        </li>
      ";
        }
        // line 297
        echo "
      <li>
        <input type=\"radio\" name=\"output_format\" value=\"sendit\" id=\"radio_dump_asfile\"";
        // line 300
        echo ((( !($context["repopulate"] ?? null) && ($context["is_checked_asfile"] ?? null))) ? (" checked") : (""));
        echo ">
        <label for=\"radio_dump_asfile\">
          ";
        // line 302
        echo _gettext("Save output to a file");
        // line 303
        echo "        </label>
        <ul id=\"ul_save_asfile\">
          ";
        // line 305
        if (($context["has_save_dir"] ?? null)) {
            // line 306
            echo "            <li>
              <input type=\"checkbox\" name=\"onserver\" value=\"saveit\" id=\"checkbox_dump_onserver\"";
            // line 307
            echo ((($context["is_checked_export"] ?? null)) ? (" checked") : (""));
            echo ">
              <label for=\"checkbox_dump_onserver\">
                ";
            // line 309
            echo twig_sprintf(_gettext("Save on server in the directory <strong>%s</strong>"), twig_escape_filter($this->env, ($context["save_dir"] ?? null)));
            echo "
              </label>
            </li>
            <li>
              <input type=\"checkbox\" name=\"onserver_overwrite\" value=\"saveitover\" id=\"checkbox_dump_onserver_overwrite\"";
            // line 314
            echo ((($context["is_checked_export_overwrite"] ?? null)) ? (" checked") : (""));
            echo ">
              <label for=\"checkbox_dump_onserver_overwrite\">
                ";
            // line 316
            echo _gettext("Overwrite existing file(s)");
            // line 317
            echo "              </label>
            </li>
          ";
        }
        // line 320
        echo "
          <li>
            <label for=\"filename_template\" class=\"desc\">
              ";
        // line 323
        echo _gettext("File name template:");
        // line 324
        echo "              ";
        echo \PhpMyAdmin\Html\Generator::showHint(twig_sprintf(_gettext("This value is interpreted using the 'strftime' function, so you can use time formatting strings. Additionally the following transformations will happen: %s Other text will be kept as is. See the FAQ 6.27 for details."), ($context["filename_hint"] ?? null)));
        echo "
            </label>
            <input type=\"text\" name=\"filename_template\" id=\"filename_template\" value=\"";
        // line 326
        echo twig_escape_filter($this->env, ($context["filename_template"] ?? null), "html", null, true);
        echo "\">
            <input type=\"checkbox\" name=\"remember_template\" id=\"checkbox_remember_template\"";
        // line 327
        echo ((($context["is_checked_remember_file_template"] ?? null)) ? (" checked") : (""));
        echo ">
            <label for=\"checkbox_remember_template\">
              ";
        // line 329
        echo _gettext("use this for future exports");
        // line 330
        echo "            </label>
          </li>

          ";
        // line 333
        if (($context["is_encoding_supported"] ?? null)) {
            // line 334
            echo "            <li>
              <label for=\"select_charset\" class=\"desc\">
                ";
            // line 336
            echo _gettext("Character set of the file:");
            // line 337
            echo "              </label>
              <select id=\"select_charset\" name=\"charset\" size=\"1\">
                ";
            // line 339
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable(($context["encodings"] ?? null));
            foreach ($context['_seq'] as $context["_key"] => $context["charset"]) {
                // line 340
                echo "                  <option value=\"";
                echo twig_escape_filter($this->env, $context["charset"], "html", null, true);
                echo "\"";
                // line 341
                echo ((((twig_test_empty(($context["export_charset"] ?? null)) && ($context["charset"] == "utf-8")) || ($context["charset"] == ($context["export_charset"] ?? null)))) ? (" selected") : (""));
                echo ">";
                // line 342
                echo twig_escape_filter($this->env, $context["charset"], "html", null, true);
                // line 343
                echo "</option>
                ";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['charset'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 345
            echo "              </select>
            </li>
          ";
        }
        // line 348
        echo "
          ";
        // line 349
        if ((($context["has_zip"] ?? null) || ($context["has_gzip"] ?? null))) {
            // line 350
            echo "            <li>
              <label for=\"compression\" class=\"desc\">
                ";
            // line 352
            echo _gettext("Compression:");
            // line 353
            echo "              </label>
              <select id=\"compression\" name=\"compression\">
                <option value=\"none\">";
            // line 355
            echo _gettext("None");
            echo "</option>
                ";
            // line 356
            if (($context["has_zip"] ?? null)) {
                // line 357
                echo "                  <option value=\"zip\"";
                // line 358
                echo (((($context["selected_compression"] ?? null) == "zip")) ? (" selected") : (""));
                echo ">
                    ";
                // line 359
                echo _gettext("zipped");
                // line 360
                echo "                  </option>
                ";
            }
            // line 362
            echo "                ";
            if (($context["has_gzip"] ?? null)) {
                // line 363
                echo "                  <option value=\"gzip\"";
                // line 364
                echo (((($context["selected_compression"] ?? null) == "gzip")) ? (" selected") : (""));
                echo ">
                    ";
                // line 365
                echo _gettext("gzipped");
                // line 366
                echo "                  </option>
                ";
            }
            // line 368
            echo "              </select>
            </li>
          ";
        } else {
            // line 371
            echo "            <input type=\"hidden\" name=\"compression\" value=\"";
            echo twig_escape_filter($this->env, ($context["selected_compression"] ?? null), "html", null, true);
            echo "\">
          ";
        }
        // line 373
        echo "
          ";
        // line 374
        if (((($context["export_type"] ?? null) == "server") || (($context["export_type"] ?? null) == "database"))) {
            // line 375
            echo "            <li>
              <input type=\"checkbox\" id=\"checkbox_as_separate_files\" name=\"as_separate_files\" value=\"";
            // line 376
            echo twig_escape_filter($this->env, ($context["export_type"] ?? null), "html", null, true);
            echo "\"";
            // line 377
            echo ((($context["is_checked_as_separate_files"] ?? null)) ? (" checked") : (""));
            echo ">
              <label for=\"checkbox_as_separate_files\">
                ";
            // line 379
            if ((($context["export_type"] ?? null) == "server")) {
                // line 380
                echo "                  ";
                echo _gettext("Export databases as separate files");
                // line 381
                echo "                ";
            } elseif ((($context["export_type"] ?? null) == "database")) {
                // line 382
                echo "                  ";
                echo _gettext("Export tables as separate files");
                // line 383
                echo "                ";
            }
            // line 384
            echo "              </label>
            </li>
          ";
        }
        // line 387
        echo "        </ul>
      </li>

      <li>
        <input type=\"radio\" id=\"radio_view_as_text\" name=\"output_format\" value=\"astext\"";
        // line 392
        echo (((($context["repopulate"] ?? null) || (($context["export_asfile"] ?? null) == false))) ? (" checked") : (""));
        echo ">
        <label for=\"radio_view_as_text\">
          ";
        // line 394
        echo _gettext("View output as text");
        // line 395
        echo "        </label>
      </li>
    </ul>

    <label for=\"maxsize\">";
        // line 400
        echo twig_sprintf(_gettext("Skip tables larger than %s MiB"), "</label><input type=\"text\" id=\"maxsize\" name=\"maxsize\" size=\"4\">");
        // line 402
        echo "
  </div>

  <div class=\"exportoptions\" id=\"format_specific_opts\">
    <h3>";
        // line 406
        echo _gettext("Format-specific options:");
        echo "</h3>
    <p class=\"no_js_msg\" id=\"scroll_to_options_msg\">
      ";
        // line 408
        echo _gettext("Scroll down to fill in the options for the selected format and ignore the options for other formats.");
        // line 409
        echo "    </p>
    ";
        // line 410
        echo ($context["options"] ?? null);
        echo "
  </div>

  ";
        // line 413
        if (($context["can_convert_kanji"] ?? null)) {
            // line 414
            echo "    ";
            // line 415
            echo "    <div class=\"exportoptions\" id=\"kanji_encoding\">
      <h3>";
            // line 416
            echo _gettext("Encoding Conversion:");
            echo "</h3>
      ";
            // line 417
            $this->loadTemplate("encoding/kanji_encoding_form.twig", "export.twig", 417)->display($context);
            // line 418
            echo "    </div>
  ";
        }
        // line 420
        echo "
  <div class=\"exportoptions justify-content-end\" id=\"submit\">
    <input id=\"buttonGo\" class=\"btn btn-primary\" type=\"submit\" value=\"";
        // line 422
        echo _gettext("Go");
        echo "\" data-exec-time-limit=\"";
        echo twig_escape_filter($this->env, ($context["exec_time_limit"] ?? null), "html", null, true);
        echo "\">
  </div>
</form>
";
    }

    // line 4
    public function block_message($context, array $blocks = [])
    {
        $macros = $this->macros;
    }

    // line 9
    public function block_title($context, array $blocks = [])
    {
        $macros = $this->macros;
    }

    // line 98
    public function block_selection_options($context, array $blocks = [])
    {
        $macros = $this->macros;
    }

    public function getTemplateName()
    {
        return "export.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  945 => 98,  939 => 9,  933 => 4,  923 => 422,  919 => 420,  915 => 418,  913 => 417,  909 => 416,  906 => 415,  904 => 414,  902 => 413,  896 => 410,  893 => 409,  891 => 408,  886 => 406,  880 => 402,  878 => 400,  872 => 395,  870 => 394,  865 => 392,  859 => 387,  854 => 384,  851 => 383,  848 => 382,  845 => 381,  842 => 380,  840 => 379,  835 => 377,  832 => 376,  829 => 375,  827 => 374,  824 => 373,  818 => 371,  813 => 368,  809 => 366,  807 => 365,  803 => 364,  801 => 363,  798 => 362,  794 => 360,  792 => 359,  788 => 358,  786 => 357,  784 => 356,  780 => 355,  776 => 353,  774 => 352,  770 => 350,  768 => 349,  765 => 348,  760 => 345,  753 => 343,  751 => 342,  748 => 341,  744 => 340,  740 => 339,  736 => 337,  734 => 336,  730 => 334,  728 => 333,  723 => 330,  721 => 329,  716 => 327,  712 => 326,  706 => 324,  704 => 323,  699 => 320,  694 => 317,  692 => 316,  687 => 314,  680 => 309,  675 => 307,  672 => 306,  670 => 305,  666 => 303,  664 => 302,  659 => 300,  655 => 297,  648 => 293,  643 => 291,  640 => 289,  638 => 288,  633 => 285,  631 => 284,  626 => 282,  620 => 279,  610 => 272,  604 => 269,  595 => 263,  587 => 258,  581 => 255,  572 => 249,  564 => 244,  558 => 241,  549 => 235,  541 => 230,  529 => 221,  519 => 213,  515 => 210,  509 => 209,  503 => 208,  493 => 204,  481 => 201,  472 => 199,  468 => 198,  465 => 197,  461 => 196,  458 => 195,  451 => 191,  441 => 188,  434 => 186,  430 => 185,  427 => 184,  424 => 183,  420 => 182,  417 => 181,  410 => 177,  402 => 174,  397 => 172,  393 => 171,  390 => 170,  387 => 169,  383 => 168,  376 => 163,  374 => 162,  366 => 157,  363 => 156,  356 => 151,  354 => 150,  349 => 148,  342 => 143,  337 => 141,  331 => 138,  328 => 137,  326 => 136,  323 => 135,  315 => 130,  311 => 129,  303 => 123,  299 => 121,  294 => 118,  291 => 117,  288 => 115,  286 => 114,  284 => 113,  282 => 112,  278 => 110,  272 => 107,  268 => 106,  262 => 102,  259 => 101,  257 => 100,  254 => 99,  252 => 98,  246 => 95,  242 => 94,  238 => 92,  231 => 87,  229 => 86,  224 => 84,  218 => 79,  216 => 78,  211 => 76,  205 => 72,  202 => 71,  200 => 70,  195 => 68,  191 => 67,  188 => 66,  177 => 58,  168 => 53,  161 => 49,  158 => 47,  156 => 46,  153 => 45,  141 => 38,  135 => 37,  132 => 36,  123 => 33,  116 => 32,  112 => 31,  108 => 30,  103 => 28,  99 => 27,  90 => 21,  86 => 20,  82 => 19,  78 => 18,  72 => 15,  69 => 14,  67 => 13,  62 => 10,  60 => 9,  56 => 8,  51 => 5,  49 => 4,  44 => 2,  40 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "export.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/export.twig");
    }
}
