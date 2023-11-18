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

/* database/structure/structure_table_row.twig */
class __TwigTemplate_ec718349ed33a5d4ac10c780d57f1e23b8b02dca7c5061f644712ff9536d4e9e extends \Twig\Template
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
        echo "<tr id=\"row_tbl_";
        echo twig_escape_filter($this->env, ($context["curr"] ?? null), "html", null, true);
        echo "\"";
        echo ((($context["table_is_view"] ?? null)) ? (" class=\"is_view\"") : (""));
        echo " data-filter-row=\"";
        echo twig_escape_filter($this->env, twig_upper_filter($this->env, (($__internal_compile_0 = ($context["current_table"] ?? null)) && is_array($__internal_compile_0) || $__internal_compile_0 instanceof ArrayAccess ? ($__internal_compile_0["TABLE_NAME"] ?? null) : null)), "html", null, true);
        echo "\">
    <td class=\"text-center d-print-none\">
        <input type=\"checkbox\"
            name=\"selected_tbl[]\"
            class=\"";
        // line 5
        echo twig_escape_filter($this->env, ($context["input_class"] ?? null), "html", null, true);
        echo "\"
            value=\"";
        // line 6
        echo twig_escape_filter($this->env, (($__internal_compile_1 = ($context["current_table"] ?? null)) && is_array($__internal_compile_1) || $__internal_compile_1 instanceof ArrayAccess ? ($__internal_compile_1["TABLE_NAME"] ?? null) : null), "html", null, true);
        echo "\"
            id=\"checkbox_tbl_";
        // line 7
        echo twig_escape_filter($this->env, ($context["curr"] ?? null), "html", null, true);
        echo "\">
    </td>
    <th>
        <a href=\"";
        // line 10
        echo PhpMyAdmin\Url::getFromRoute("/sql", twig_array_merge(($context["table_url_params"] ?? null), ["pos" => 0]));
        echo "\" title=\"";
        echo twig_escape_filter($this->env, ($context["browse_table_label_title"] ?? null), "html", null, true);
        echo "\">
            ";
        // line 11
        echo twig_escape_filter($this->env, ($context["browse_table_label_truename"] ?? null), "html", null, true);
        echo "
        </a>
        ";
        // line 13
        echo ($context["tracking_icon"] ?? null);
        echo "
    </th>
    ";
        // line 15
        if (($context["server_slave_status"] ?? null)) {
            // line 16
            echo "        <td class=\"text-center\">
            ";
            // line 17
            echo ((($context["ignored"] ?? null)) ? (\PhpMyAdmin\Html\Generator::getImage("s_cancel", _gettext("Not replicated"))) : (""));
            echo "
            ";
            // line 18
            echo ((($context["do"] ?? null)) ? (\PhpMyAdmin\Html\Generator::getImage("s_success", _gettext("Replicated"))) : (""));
            echo "
        </td>
    ";
        }
        // line 21
        echo "
    ";
        // line 23
        echo "    ";
        if ((($context["num_favorite_tables"] ?? null) > 0)) {
            // line 24
            echo "        <td class=\"text-center d-print-none\">
            ";
            // line 26
            echo "            ";
            $context["fav_params"] = ["db" =>             // line 27
($context["db"] ?? null), "ajax_request" => true, "favorite_table" => (($__internal_compile_2 =             // line 29
($context["current_table"] ?? null)) && is_array($__internal_compile_2) || $__internal_compile_2 instanceof ArrayAccess ? ($__internal_compile_2["TABLE_NAME"] ?? null) : null), (((            // line 30
($context["already_favorite"] ?? null)) ? ("remove") : ("add")) . "_favorite") => true];
            // line 32
            echo "            ";
            $this->loadTemplate("database/structure/favorite_anchor.twig", "database/structure/structure_table_row.twig", 32)->display(twig_to_array(["table_name_hash" =>             // line 33
($context["table_name_hash"] ?? null), "db_table_name_hash" =>             // line 34
($context["db_table_name_hash"] ?? null), "fav_params" =>             // line 35
($context["fav_params"] ?? null), "already_favorite" =>             // line 36
($context["already_favorite"] ?? null)]));
            // line 38
            echo "        </td>
    ";
        }
        // line 40
        echo "
    <td class=\"text-center d-print-none\">
        <a href=\"";
        // line 42
        echo PhpMyAdmin\Url::getFromRoute("/sql", twig_array_merge(($context["table_url_params"] ?? null), ["pos" => 0]));
        echo "\">
          ";
        // line 43
        echo ((($context["may_have_rows"] ?? null)) ? (\PhpMyAdmin\Html\Generator::getIcon("b_browse", _gettext("Browse"))) : (\PhpMyAdmin\Html\Generator::getIcon("bd_browse", _gettext("Browse"))));
        echo "
        </a>
    </td>
    <td class=\"text-center d-print-none\">
        <a href=\"";
        // line 47
        echo PhpMyAdmin\Url::getFromRoute("/table/structure", ($context["table_url_params"] ?? null));
        echo "\">
          ";
        // line 48
        echo \PhpMyAdmin\Html\Generator::getIcon("b_props", _gettext("Structure"));
        echo "
        </a>
    </td>
    <td class=\"text-center d-print-none\">
        <a href=\"";
        // line 52
        echo PhpMyAdmin\Url::getFromRoute("/table/search", ($context["table_url_params"] ?? null));
        echo "\">
          ";
        // line 53
        echo ((($context["may_have_rows"] ?? null)) ? (\PhpMyAdmin\Html\Generator::getIcon("b_select", _gettext("Search"))) : (\PhpMyAdmin\Html\Generator::getIcon("bd_select", _gettext("Search"))));
        echo "
        </a>
    </td>

    ";
        // line 57
        if ( !($context["db_is_system_schema"] ?? null)) {
            // line 58
            echo "        <td class=\"insert_table text-center d-print-none\">
            <a href=\"";
            // line 59
            echo PhpMyAdmin\Url::getFromRoute("/table/change", ($context["table_url_params"] ?? null));
            echo "\">";
            echo \PhpMyAdmin\Html\Generator::getIcon("b_insrow", _gettext("Insert"));
            echo "</a>
        </td>
        ";
            // line 61
            if (($context["table_is_view"] ?? null)) {
                // line 62
                echo "            <td class=\"text-center d-print-none\">
                <a href=\"";
                // line 63
                echo PhpMyAdmin\Url::getFromRoute("/view/create", ["db" =>                 // line 64
($context["db"] ?? null), "table" => (($__internal_compile_3 =                 // line 65
($context["current_table"] ?? null)) && is_array($__internal_compile_3) || $__internal_compile_3 instanceof ArrayAccess ? ($__internal_compile_3["TABLE_NAME"] ?? null) : null)]);
                // line 66
                echo "\">";
                echo \PhpMyAdmin\Html\Generator::getIcon("b_edit", _gettext("Edit"));
                echo "</a>
            </td>
        ";
            } else {
                // line 69
                echo "          <td class=\"text-center d-print-none\">
                <a class=\"truncate_table_anchor ajax\" href=\"";
                // line 70
                echo PhpMyAdmin\Url::getFromRoute("/sql");
                echo "\" data-post=\"";
                echo PhpMyAdmin\Url::getCommon(twig_array_merge(($context["table_url_params"] ?? null), ["sql_query" =>                 // line 71
($context["empty_table_sql_query"] ?? null), "message_to_show" =>                 // line 72
($context["empty_table_message_to_show"] ?? null)]), "");
                // line 73
                echo "\">
                  ";
                // line 74
                echo ((($context["may_have_rows"] ?? null)) ? (\PhpMyAdmin\Html\Generator::getIcon("b_empty", _gettext("Empty"))) : (\PhpMyAdmin\Html\Generator::getIcon("bd_empty", _gettext("Empty"))));
                echo "
                </a>
          </td>
        ";
            }
            // line 78
            echo "        <td class=\"text-center d-print-none\">
            <a class=\"ajax drop_table_anchor";
            // line 80
            echo (((($context["table_is_view"] ?? null) || ((($__internal_compile_4 = ($context["current_table"] ?? null)) && is_array($__internal_compile_4) || $__internal_compile_4 instanceof ArrayAccess ? ($__internal_compile_4["ENGINE"] ?? null) : null) == null))) ? (" view") : (""));
            echo "\" href=\"";
            echo PhpMyAdmin\Url::getFromRoute("/sql");
            echo "\" data-post=\"";
            // line 81
            echo PhpMyAdmin\Url::getCommon(twig_array_merge(($context["table_url_params"] ?? null), ["reload" => 1, "purge" => 1, "sql_query" =>             // line 84
($context["drop_query"] ?? null), "message_to_show" =>             // line 85
($context["drop_message"] ?? null)]), "");
            // line 86
            echo "\">
                ";
            // line 87
            echo \PhpMyAdmin\Html\Generator::getIcon("b_drop", _gettext("Drop"));
            echo "
            </a>
        </td>
    ";
        }
        // line 91
        echo "
    ";
        // line 92
        if ((twig_get_attribute($this->env, $this->source, ($context["current_table"] ?? null), "TABLE_ROWS", [], "array", true, true, false, 92) && (((($__internal_compile_5 =         // line 93
($context["current_table"] ?? null)) && is_array($__internal_compile_5) || $__internal_compile_5 instanceof ArrayAccess ? ($__internal_compile_5["ENGINE"] ?? null) : null) != null) || ($context["table_is_view"] ?? null)))) {
            // line 94
            echo "        ";
            // line 95
            echo "        ";
            $context["row_count"] = PhpMyAdmin\Util::formatNumber((($__internal_compile_6 = ($context["current_table"] ?? null)) && is_array($__internal_compile_6) || $__internal_compile_6 instanceof ArrayAccess ? ($__internal_compile_6["TABLE_ROWS"] ?? null) : null), 0);
            // line 96
            echo "
        ";
            // line 99
            echo "        <td class=\"value tbl_rows text-monospace text-right\"
            data-table=\"";
            // line 100
            echo twig_escape_filter($this->env, (($__internal_compile_7 = ($context["current_table"] ?? null)) && is_array($__internal_compile_7) || $__internal_compile_7 instanceof ArrayAccess ? ($__internal_compile_7["TABLE_NAME"] ?? null) : null), "html", null, true);
            echo "\">
            ";
            // line 101
            if (($context["approx_rows"] ?? null)) {
                // line 102
                echo "                <a href=\"";
                echo PhpMyAdmin\Url::getFromRoute("/database/structure/real-row-count", ["ajax_request" => true, "db" =>                 // line 104
($context["db"] ?? null), "table" => (($__internal_compile_8 =                 // line 105
($context["current_table"] ?? null)) && is_array($__internal_compile_8) || $__internal_compile_8 instanceof ArrayAccess ? ($__internal_compile_8["TABLE_NAME"] ?? null) : null)]);
                // line 106
                echo "\" class=\"ajax real_row_count\">
                    <bdi>
                        ~";
                // line 108
                echo twig_escape_filter($this->env, ($context["row_count"] ?? null), "html", null, true);
                echo "
                    </bdi>
                </a>
            ";
            } else {
                // line 112
                echo "                ";
                echo twig_escape_filter($this->env, ($context["row_count"] ?? null), "html", null, true);
                echo "
            ";
            }
            // line 114
            echo "            ";
            echo ($context["show_superscript"] ?? null);
            echo "
        </td>

        ";
            // line 117
            if ( !(($context["properties_num_columns"] ?? null) > 1)) {
                // line 118
                echo "            <td class=\"nowrap\">
                ";
                // line 119
                if ( !twig_test_empty((($__internal_compile_9 = ($context["current_table"] ?? null)) && is_array($__internal_compile_9) || $__internal_compile_9 instanceof ArrayAccess ? ($__internal_compile_9["ENGINE"] ?? null) : null))) {
                    // line 120
                    echo "                    ";
                    echo twig_escape_filter($this->env, (($__internal_compile_10 = ($context["current_table"] ?? null)) && is_array($__internal_compile_10) || $__internal_compile_10 instanceof ArrayAccess ? ($__internal_compile_10["ENGINE"] ?? null) : null), "html", null, true);
                    echo "
                ";
                } elseif (                // line 121
($context["table_is_view"] ?? null)) {
                    // line 122
                    echo "                    ";
                    echo _gettext("View");
                    // line 123
                    echo "                ";
                }
                // line 124
                echo "            </td>
            ";
                // line 125
                if ((twig_length_filter($this->env, ($context["collation"] ?? null)) > 0)) {
                    // line 126
                    echo "                <td class=\"nowrap\">
                    ";
                    // line 127
                    echo ($context["collation"] ?? null);
                    echo "
                </td>
            ";
                }
                // line 130
                echo "        ";
            }
            // line 131
            echo "
        ";
            // line 132
            if (($context["is_show_stats"] ?? null)) {
                // line 133
                echo "            <td class=\"value tbl_size text-monospace text-right\">
                <a href=\"";
                // line 134
                echo PhpMyAdmin\Url::getFromRoute("/table/structure", ($context["table_url_params"] ?? null));
                echo "#showusage\">
                    <span>";
                // line 135
                echo twig_escape_filter($this->env, ($context["formatted_size"] ?? null), "html", null, true);
                echo "</span>&nbsp;<span class=\"unit\">";
                echo twig_escape_filter($this->env, ($context["unit"] ?? null), "html", null, true);
                echo "</span>
                </a>
            </td>
            <td class=\"value tbl_overhead text-monospace text-right\">
                ";
                // line 139
                echo ($context["overhead"] ?? null);
                echo "
            </td>
        ";
            }
            // line 142
            echo "
        ";
            // line 143
            if ( !(($context["show_charset"] ?? null) > 1)) {
                // line 144
                echo "            ";
                if ((twig_length_filter($this->env, ($context["charset"] ?? null)) > 0)) {
                    // line 145
                    echo "                <td class=\"nowrap\">
                    ";
                    // line 146
                    echo ($context["charset"] ?? null);
                    echo "
                </td>
            ";
                }
                // line 149
                echo "        ";
            }
            // line 150
            echo "
        ";
            // line 151
            if (($context["show_comment"] ?? null)) {
                // line 152
                echo "            ";
                $context["comment"] = (($__internal_compile_11 = ($context["current_table"] ?? null)) && is_array($__internal_compile_11) || $__internal_compile_11 instanceof ArrayAccess ? ($__internal_compile_11["Comment"] ?? null) : null);
                // line 153
                echo "            <td>
                ";
                // line 154
                if ((twig_length_filter($this->env, ($context["comment"] ?? null)) > ($context["limit_chars"] ?? null))) {
                    // line 155
                    echo "                    <abbr title=\"";
                    echo twig_escape_filter($this->env, ($context["comment"] ?? null), "html", null, true);
                    echo "\">
                        ";
                    // line 156
                    echo twig_escape_filter($this->env, twig_slice($this->env, ($context["comment"] ?? null), 0, ($context["limit_chars"] ?? null)), "html", null, true);
                    echo "
                        ...
                    </abbr>
                ";
                } else {
                    // line 160
                    echo "                    ";
                    echo twig_escape_filter($this->env, ($context["comment"] ?? null), "html", null, true);
                    echo "
                ";
                }
                // line 162
                echo "            </td>
        ";
            }
            // line 164
            echo "
        ";
            // line 165
            if (($context["show_creation"] ?? null)) {
                // line 166
                echo "            <td class=\"value tbl_creation text-monospace text-right\">
                ";
                // line 167
                echo twig_escape_filter($this->env, ($context["create_time"] ?? null), "html", null, true);
                echo "
            </td>
        ";
            }
            // line 170
            echo "
        ";
            // line 171
            if (($context["show_last_update"] ?? null)) {
                // line 172
                echo "            <td class=\"value tbl_last_update text-monospace text-right\">
                ";
                // line 173
                echo twig_escape_filter($this->env, ($context["update_time"] ?? null), "html", null, true);
                echo "
            </td>
        ";
            }
            // line 176
            echo "
        ";
            // line 177
            if (($context["show_last_check"] ?? null)) {
                // line 178
                echo "            <td class=\"value tbl_last_check text-monospace text-right\">
                ";
                // line 179
                echo twig_escape_filter($this->env, ($context["check_time"] ?? null), "html", null, true);
                echo "
            </td>
        ";
            }
            // line 182
            echo "
    ";
        } elseif (        // line 183
($context["table_is_view"] ?? null)) {
            // line 184
            echo "        <td class=\"value tbl_rows text-monospace text-right\">-</td>
        <td class=\"nowrap\">
            ";
            // line 186
            echo _gettext("View");
            // line 187
            echo "        </td>
        <td class=\"nowrap\">---</td>
        ";
            // line 189
            if (($context["is_show_stats"] ?? null)) {
                // line 190
                echo "            <td class=\"value tbl_size text-monospace text-right\">-</td>
            <td class=\"value tbl_overhead text-monospace text-right\">-</td>
        ";
            }
            // line 193
            echo "        ";
            if (($context["show_charset"] ?? null)) {
                // line 194
                echo "            <td></td>
        ";
            }
            // line 196
            echo "        ";
            if (($context["show_comment"] ?? null)) {
                // line 197
                echo "            <td></td>
        ";
            }
            // line 199
            echo "        ";
            if (($context["show_creation"] ?? null)) {
                // line 200
                echo "            <td class=\"value tbl_creation text-monospace text-right\">-</td>
        ";
            }
            // line 202
            echo "        ";
            if (($context["show_last_update"] ?? null)) {
                // line 203
                echo "            <td class=\"value tbl_last_update text-monospace text-right\">-</td>
        ";
            }
            // line 205
            echo "        ";
            if (($context["show_last_check"] ?? null)) {
                // line 206
                echo "            <td class=\"value tbl_last_check text-monospace text-right\">-</td>
        ";
            }
            // line 208
            echo "
    ";
        } else {
            // line 210
            echo "
        ";
            // line 211
            if (($context["db_is_system_schema"] ?? null)) {
                // line 212
                echo "            ";
                $context["action_colspan"] = 3;
                // line 213
                echo "        ";
            } else {
                // line 214
                echo "            ";
                $context["action_colspan"] = 6;
                // line 215
                echo "        ";
            }
            // line 216
            echo "        ";
            if ((($context["num_favorite_tables"] ?? null) > 0)) {
                // line 217
                echo "            ";
                $context["action_colspan"] = (($context["action_colspan"] ?? null) + 1);
                // line 218
                echo "        ";
            }
            // line 219
            echo "
        ";
            // line 220
            $context["colspan_for_structure"] = (($context["action_colspan"] ?? null) + 3);
            // line 221
            echo "        <td colspan=\"";
            echo (((($context["colspan_for_structure"] ?? null) - ($context["db_is_system_schema"] ?? null))) ? (6) : (9));
            echo "\"
            class=\"text-center\">
            ";
            // line 223
            echo _gettext("in use");
            // line 224
            echo "        </td>
    ";
        }
        // line 226
        echo "</tr>
";
    }

    public function getTemplateName()
    {
        return "database/structure/structure_table_row.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  543 => 226,  539 => 224,  537 => 223,  531 => 221,  529 => 220,  526 => 219,  523 => 218,  520 => 217,  517 => 216,  514 => 215,  511 => 214,  508 => 213,  505 => 212,  503 => 211,  500 => 210,  496 => 208,  492 => 206,  489 => 205,  485 => 203,  482 => 202,  478 => 200,  475 => 199,  471 => 197,  468 => 196,  464 => 194,  461 => 193,  456 => 190,  454 => 189,  450 => 187,  448 => 186,  444 => 184,  442 => 183,  439 => 182,  433 => 179,  430 => 178,  428 => 177,  425 => 176,  419 => 173,  416 => 172,  414 => 171,  411 => 170,  405 => 167,  402 => 166,  400 => 165,  397 => 164,  393 => 162,  387 => 160,  380 => 156,  375 => 155,  373 => 154,  370 => 153,  367 => 152,  365 => 151,  362 => 150,  359 => 149,  353 => 146,  350 => 145,  347 => 144,  345 => 143,  342 => 142,  336 => 139,  327 => 135,  323 => 134,  320 => 133,  318 => 132,  315 => 131,  312 => 130,  306 => 127,  303 => 126,  301 => 125,  298 => 124,  295 => 123,  292 => 122,  290 => 121,  285 => 120,  283 => 119,  280 => 118,  278 => 117,  271 => 114,  265 => 112,  258 => 108,  254 => 106,  252 => 105,  251 => 104,  249 => 102,  247 => 101,  243 => 100,  240 => 99,  237 => 96,  234 => 95,  232 => 94,  230 => 93,  229 => 92,  226 => 91,  219 => 87,  216 => 86,  214 => 85,  213 => 84,  212 => 81,  207 => 80,  204 => 78,  197 => 74,  194 => 73,  192 => 72,  191 => 71,  188 => 70,  185 => 69,  178 => 66,  176 => 65,  175 => 64,  174 => 63,  171 => 62,  169 => 61,  162 => 59,  159 => 58,  157 => 57,  150 => 53,  146 => 52,  139 => 48,  135 => 47,  128 => 43,  124 => 42,  120 => 40,  116 => 38,  114 => 36,  113 => 35,  112 => 34,  111 => 33,  109 => 32,  107 => 30,  106 => 29,  105 => 27,  103 => 26,  100 => 24,  97 => 23,  94 => 21,  88 => 18,  84 => 17,  81 => 16,  79 => 15,  74 => 13,  69 => 11,  63 => 10,  57 => 7,  53 => 6,  49 => 5,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "database/structure/structure_table_row.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/database/structure/structure_table_row.twig");
    }
}
