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

/* display/results/null_display.twig */
class __TwigTemplate_29c269688610555a694d8a3ab3ba687f1588eb9e83d66c4356fa2c28c14a3226 extends \Twig\Template
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
        echo "<td ";
        echo twig_escape_filter($this->env, ($context["align"] ?? null), "html", null, true);
        echo "
    data-decimals=\"";
        // line 2
        ((twig_get_attribute($this->env, $this->source, ($context["meta"] ?? null), "decimals", [], "any", true, true, false, 2)) ? (print (twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["meta"] ?? null), "decimals", [], "any", false, false, false, 2), "html", null, true))) : (print ("-1")));
        echo "\"
    data-type=\"";
        // line 3
        echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["meta"] ?? null), "type", [], "any", false, false, false, 3), "html", null, true);
        echo "\"
    ";
        // line 5
        echo "    class=\"";
        echo twig_escape_filter($this->env, ($context["classes"] ?? null), "html", null, true);
        echo " null\">
    <em>NULL</em>
</td>
";
    }

    public function getTemplateName()
    {
        return "display/results/null_display.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  50 => 5,  46 => 3,  42 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "display/results/null_display.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/display/results/null_display.twig");
    }
}
