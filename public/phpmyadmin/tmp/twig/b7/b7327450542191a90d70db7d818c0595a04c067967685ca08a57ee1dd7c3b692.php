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

/* display/results/comment_for_row.twig */
class __TwigTemplate_fac3899bab2e411698a92af586146beb6061c65275ae811ed2bed6614b503d5f extends \Twig\Template
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
        if ((twig_get_attribute($this->env, $this->source, ($context["comments_map"] ?? null), twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "table", [], "any", false, false, false, 1), [], "array", true, true, false, 1) && twig_get_attribute($this->env, $this->source, twig_get_attribute($this->env, $this->source,         // line 2
($context["comments_map"] ?? null), twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "table", [], "any", false, false, false, 2), [], "array", false, true, false, 2), twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "name", [], "any", false, false, false, 2), [], "array", true, true, false, 2))) {
            // line 3
            echo "    <br><span class=\"tblcomment\" title=\"";
            echo twig_escape_filter($this->env, (($__internal_compile_0 = (($__internal_compile_1 = ($context["comments_map"] ?? null)) && is_array($__internal_compile_1) || $__internal_compile_1 instanceof ArrayAccess ? ($__internal_compile_1[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "table", [], "any", false, false, false, 3)] ?? null) : null)) && is_array($__internal_compile_0) || $__internal_compile_0 instanceof ArrayAccess ? ($__internal_compile_0[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "name", [], "any", false, false, false, 3)] ?? null) : null), "html", null, true);
            echo "\">
        ";
            // line 4
            if ((twig_length_filter($this->env, (($__internal_compile_2 = (($__internal_compile_3 = ($context["comments_map"] ?? null)) && is_array($__internal_compile_3) || $__internal_compile_3 instanceof ArrayAccess ? ($__internal_compile_3[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "table", [], "any", false, false, false, 4)] ?? null) : null)) && is_array($__internal_compile_2) || $__internal_compile_2 instanceof ArrayAccess ? ($__internal_compile_2[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "name", [], "any", false, false, false, 4)] ?? null) : null)) > ($context["limit_chars"] ?? null))) {
                // line 5
                echo "            ";
                echo twig_escape_filter($this->env, twig_slice($this->env, (($__internal_compile_4 = (($__internal_compile_5 = ($context["comments_map"] ?? null)) && is_array($__internal_compile_5) || $__internal_compile_5 instanceof ArrayAccess ? ($__internal_compile_5[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "table", [], "any", false, false, false, 5)] ?? null) : null)) && is_array($__internal_compile_4) || $__internal_compile_4 instanceof ArrayAccess ? ($__internal_compile_4[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "name", [], "any", false, false, false, 5)] ?? null) : null), 0, ($context["limit_chars"] ?? null)), "html", null, true);
                echo "…
        ";
            } else {
                // line 7
                echo "            ";
                echo twig_escape_filter($this->env, (($__internal_compile_6 = (($__internal_compile_7 = ($context["comments_map"] ?? null)) && is_array($__internal_compile_7) || $__internal_compile_7 instanceof ArrayAccess ? ($__internal_compile_7[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "table", [], "any", false, false, false, 7)] ?? null) : null)) && is_array($__internal_compile_6) || $__internal_compile_6 instanceof ArrayAccess ? ($__internal_compile_6[twig_get_attribute($this->env, $this->source, ($context["fields_meta"] ?? null), "name", [], "any", false, false, false, 7)] ?? null) : null), "html", null, true);
                echo "
        ";
            }
            // line 9
            echo "    </span>
";
        }
    }

    public function getTemplateName()
    {
        return "display/results/comment_for_row.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  59 => 9,  53 => 7,  47 => 5,  45 => 4,  40 => 3,  38 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "display/results/comment_for_row.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/display/results/comment_for_row.twig");
    }
}
