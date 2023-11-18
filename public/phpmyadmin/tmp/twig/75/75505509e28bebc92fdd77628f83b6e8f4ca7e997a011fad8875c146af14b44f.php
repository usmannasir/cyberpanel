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

/* config/form_display/fieldset_top.twig */
class __TwigTemplate_d15c6f4af6bec66064dab006b9d3bd859701484f8b34f4089bd95fce24aa9b95 extends \Twig\Template
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
        echo "<fieldset";
        // line 2
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["attributes"] ?? null));
        foreach ($context['_seq'] as $context["key"] => $context["value"]) {
            // line 3
            echo " ";
            echo twig_escape_filter($this->env, $context["key"], "html", null, true);
            echo "=\"";
            echo twig_escape_filter($this->env, $context["value"], "html", null, true);
            echo "\"";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['key'], $context['value'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 4
        echo ">
<legend>";
        // line 5
        echo twig_escape_filter($this->env, ($context["title"] ?? null), "html", null, true);
        echo "</legend>
";
        // line 6
        if ( !twig_test_empty(($context["description"] ?? null))) {
            // line 7
            echo "    <p>";
            echo ($context["description"] ?? null);
            echo "</p>
";
        }
        // line 10
        if ((twig_test_iterable(($context["errors"] ?? null)) && (twig_length_filter($this->env, ($context["errors"] ?? null)) > 0))) {
            // line 11
            echo "    <dl class=\"errors\">
        ";
            // line 12
            $context['_parent'] = $context;
            $context['_seq'] = twig_ensure_traversable(($context["errors"] ?? null));
            foreach ($context['_seq'] as $context["_key"] => $context["error"]) {
                // line 13
                echo "            <dd>";
                echo twig_escape_filter($this->env, $context["error"], "html", null, true);
                echo "</dd>
        ";
            }
            $_parent = $context['_parent'];
            unset($context['_seq'], $context['_iterated'], $context['_key'], $context['error'], $context['_parent'], $context['loop']);
            $context = array_intersect_key($context, $_parent) + $_parent;
            // line 15
            echo "    </dl>
";
        }
        // line 17
        echo "<table class=\"pma-table\" width=\"100%\" cellspacing=\"0\">
";
    }

    public function getTemplateName()
    {
        return "config/form_display/fieldset_top.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  90 => 17,  86 => 15,  77 => 13,  73 => 12,  70 => 11,  68 => 10,  62 => 7,  60 => 6,  56 => 5,  53 => 4,  43 => 3,  39 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "config/form_display/fieldset_top.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/config/form_display/fieldset_top.twig");
    }
}
