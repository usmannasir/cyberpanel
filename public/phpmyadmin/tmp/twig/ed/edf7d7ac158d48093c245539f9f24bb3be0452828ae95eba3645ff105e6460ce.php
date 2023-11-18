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

/* display/results/checkbox_and_links.twig */
class __TwigTemplate_170429b0d6301c51ddfde83e90ac8d93be2c2d04fa21daa3e3e1f42a89605b48 extends \Twig\Template
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
        if ((($context["position"] ?? null) == "left")) {
            // line 2
            echo "  ";
            if (($context["has_checkbox"] ?? null)) {
                // line 3
                echo "    <td class=\"text-center print_ignore\">
      <input type=\"checkbox\" class=\"multi_checkbox checkall\" id=\"id_rows_to_delete";
                // line 5
                echo twig_escape_filter($this->env, ($context["row_number"] ?? null), "html", null, true);
                echo "_left\" name=\"rows_to_delete[";
                echo twig_escape_filter($this->env, ($context["row_number"] ?? null), "html", null, true);
                echo "]\" value=\"";
                echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                echo "\">
      <input type=\"hidden\" class=\"condition_array\" value=\"";
                // line 6
                echo twig_escape_filter($this->env, ($context["condition"] ?? null), "html", null, true);
                echo "\">
    </td>
  ";
            }
            // line 9
            echo "
  ";
            // line 10
            if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "url", [], "any", false, false, false, 10))) {
                // line 11
                echo "    <td class=\"text-center print_ignore edit_row_anchor";
                echo (( !twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "clause_is_unique", [], "any", false, false, false, 11)) ? (" nonunique") : (""));
                echo "\">
      <span class=\"nowrap\">
        ";
                // line 13
                echo PhpMyAdmin\Html\Generator::linkOrButton(twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "url", [], "any", false, false, false, 13), twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "params", [], "any", false, false, false, 13), twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "string", [], "any", false, false, false, 13));
                echo "
        ";
                // line 14
                if ( !twig_test_empty(($context["where_clause"] ?? null))) {
                    // line 15
                    echo "          <input type=\"hidden\" class=\"where_clause\" value=\"";
                    echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                    echo "\">
        ";
                }
                // line 17
                echo "      </span>
    </td>
  ";
            }
            // line 20
            echo "
  ";
            // line 21
            if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "url", [], "any", false, false, false, 21))) {
                // line 22
                echo "    <td class=\"text-center print_ignore\">
      <span class=\"nowrap\">
        ";
                // line 24
                echo PhpMyAdmin\Html\Generator::linkOrButton(twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "url", [], "any", false, false, false, 24), twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "params", [], "any", false, false, false, 24), twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "string", [], "any", false, false, false, 24));
                echo "
        ";
                // line 25
                if ( !twig_test_empty(($context["where_clause"] ?? null))) {
                    // line 26
                    echo "          <input type=\"hidden\" class=\"where_clause\" value=\"";
                    echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                    echo "\">
        ";
                }
                // line 28
                echo "      </span>
    </td>
  ";
            }
            // line 31
            echo "
  ";
            // line 32
            if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "url", [], "any", false, false, false, 32))) {
                // line 33
                echo "    <td class=\"text-center print_ignore";
                echo ((($context["is_ajax"] ?? null)) ? (" ajax") : (""));
                echo "\">
      <span class=\"nowrap\">
        ";
                // line 35
                echo PhpMyAdmin\Html\Generator::linkOrButton(twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "url", [], "any", false, false, false, 35), twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "params", [], "any", false, false, false, 35), twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "string", [], "any", false, false, false, 35), ["class" => ("delete_row requireConfirm" . ((($context["is_ajax"] ?? null)) ? (" ajax") : ("")))]);
                echo "
        ";
                // line 36
                if ( !twig_test_empty(($context["js_conf"] ?? null))) {
                    // line 37
                    echo "          <div class=\"hide\">";
                    echo twig_escape_filter($this->env, ($context["js_conf"] ?? null), "html", null, true);
                    echo "</div>
        ";
                }
                // line 39
                echo "      </span>
    </td>
  ";
            }
        } elseif ((        // line 42
($context["position"] ?? null) == "right")) {
            // line 43
            echo "  ";
            if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "url", [], "any", false, false, false, 43))) {
                // line 44
                echo "    <td class=\"text-center print_ignore";
                echo ((($context["is_ajax"] ?? null)) ? (" ajax") : (""));
                echo "\">
      <span class=\"nowrap\">
        ";
                // line 46
                echo PhpMyAdmin\Html\Generator::linkOrButton(twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "url", [], "any", false, false, false, 46), twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "params", [], "any", false, false, false, 46), twig_get_attribute($this->env, $this->source, ($context["delete"] ?? null), "string", [], "any", false, false, false, 46), ["class" => ("delete_row requireConfirm" . ((($context["is_ajax"] ?? null)) ? (" ajax") : ("")))]);
                echo "
        ";
                // line 47
                if ( !twig_test_empty(($context["js_conf"] ?? null))) {
                    // line 48
                    echo "          <div class=\"hide\">";
                    echo twig_escape_filter($this->env, ($context["js_conf"] ?? null), "html", null, true);
                    echo "</div>
        ";
                }
                // line 50
                echo "      </span>
    </td>
  ";
            }
            // line 53
            echo "
  ";
            // line 54
            if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "url", [], "any", false, false, false, 54))) {
                // line 55
                echo "    <td class=\"text-center print_ignore\">
      <span class=\"nowrap\">
        ";
                // line 57
                echo PhpMyAdmin\Html\Generator::linkOrButton(twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "url", [], "any", false, false, false, 57), twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "params", [], "any", false, false, false, 57), twig_get_attribute($this->env, $this->source, ($context["copy"] ?? null), "string", [], "any", false, false, false, 57));
                echo "
        ";
                // line 58
                if ( !twig_test_empty(($context["where_clause"] ?? null))) {
                    // line 59
                    echo "          <input type=\"hidden\" class=\"where_clause\" value=\"";
                    echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                    echo "\">
        ";
                }
                // line 61
                echo "      </span>
    </td>
  ";
            }
            // line 64
            echo "
  ";
            // line 65
            if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "url", [], "any", false, false, false, 65))) {
                // line 66
                echo "    <td class=\"text-center print_ignore edit_row_anchor";
                echo (( !twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "clause_is_unique", [], "any", false, false, false, 66)) ? (" nonunique") : (""));
                echo "\">
      <span class=\"nowrap\">
        ";
                // line 68
                echo PhpMyAdmin\Html\Generator::linkOrButton(twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "url", [], "any", false, false, false, 68), twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "params", [], "any", false, false, false, 68), twig_get_attribute($this->env, $this->source, ($context["edit"] ?? null), "string", [], "any", false, false, false, 68));
                echo "
        ";
                // line 69
                if ( !twig_test_empty(($context["where_clause"] ?? null))) {
                    // line 70
                    echo "          <input type=\"hidden\" class=\"where_clause\" value=\"";
                    echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                    echo "\">
        ";
                }
                // line 72
                echo "      </span>
    </td>
  ";
            }
            // line 75
            echo "
  ";
            // line 76
            if (($context["has_checkbox"] ?? null)) {
                // line 77
                echo "    <td class=\"text-center print_ignore\">
      <input type=\"checkbox\" class=\"multi_checkbox checkall\" id=\"id_rows_to_delete";
                // line 79
                echo twig_escape_filter($this->env, ($context["row_number"] ?? null), "html", null, true);
                echo "_right\" name=\"rows_to_delete[";
                echo twig_escape_filter($this->env, ($context["row_number"] ?? null), "html", null, true);
                echo "]\" value=\"";
                echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                echo "\">
      <input type=\"hidden\" class=\"condition_array\" value=\"";
                // line 80
                echo twig_escape_filter($this->env, ($context["condition"] ?? null), "html", null, true);
                echo "\">
    </td>
  ";
            }
        } else {
            // line 84
            echo "  ";
            if (($context["has_checkbox"] ?? null)) {
                // line 85
                echo "    <td class=\"text-center print_ignore\">
      <input type=\"checkbox\" class=\"multi_checkbox checkall\" id=\"id_rows_to_delete";
                // line 87
                echo twig_escape_filter($this->env, ($context["row_number"] ?? null), "html", null, true);
                echo "_left\" name=\"rows_to_delete[";
                echo twig_escape_filter($this->env, ($context["row_number"] ?? null), "html", null, true);
                echo "]\" value=\"";
                echo twig_escape_filter($this->env, ($context["where_clause"] ?? null), "html", null, true);
                echo "\">
      <input type=\"hidden\" class=\"condition_array\" value=\"";
                // line 88
                echo twig_escape_filter($this->env, ($context["condition"] ?? null), "html", null, true);
                echo "\">
    </td>
  ";
            }
        }
    }

    public function getTemplateName()
    {
        return "display/results/checkbox_and_links.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  260 => 88,  252 => 87,  249 => 85,  246 => 84,  239 => 80,  231 => 79,  228 => 77,  226 => 76,  223 => 75,  218 => 72,  212 => 70,  210 => 69,  206 => 68,  200 => 66,  198 => 65,  195 => 64,  190 => 61,  184 => 59,  182 => 58,  178 => 57,  174 => 55,  172 => 54,  169 => 53,  164 => 50,  158 => 48,  156 => 47,  152 => 46,  146 => 44,  143 => 43,  141 => 42,  136 => 39,  130 => 37,  128 => 36,  124 => 35,  118 => 33,  116 => 32,  113 => 31,  108 => 28,  102 => 26,  100 => 25,  96 => 24,  92 => 22,  90 => 21,  87 => 20,  82 => 17,  76 => 15,  74 => 14,  70 => 13,  64 => 11,  62 => 10,  59 => 9,  53 => 6,  45 => 5,  42 => 3,  39 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "display/results/checkbox_and_links.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/display/results/checkbox_and_links.twig");
    }
}
