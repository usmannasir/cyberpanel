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

/* display/results/table_navigation_button.twig */
class __TwigTemplate_442499bd86aeb11bd42ac5b510c6dd1f98f02b2c6a50793edc4f67be8f961af4 extends \Twig\Template
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
        echo "<td>
    <form action=\"";
        // line 2
        echo PhpMyAdmin\Url::getFromRoute("/sql");
        echo "\" method=\"post\" ";
        echo ($context["onsubmit"] ?? null);
        echo ">
        ";
        // line 3
        echo PhpMyAdmin\Url::getHiddenInputs(($context["db"] ?? null), ($context["table"] ?? null));
        echo "
        <input type=\"hidden\" name=\"sql_query\" value=\"";
        // line 4
        echo ($context["sql_query"] ?? null);
        echo "\">
        <input type=\"hidden\" name=\"pos\" value=\"";
        // line 5
        echo twig_escape_filter($this->env, ($context["pos"] ?? null), "html", null, true);
        echo "\">
        <input type=\"hidden\" name=\"is_browse_distinct\" value=\"";
        // line 6
        echo twig_escape_filter($this->env, ($context["is_browse_distinct"] ?? null), "html", null, true);
        echo "\">
        <input type=\"hidden\" name=\"goto\" value=\"";
        // line 7
        echo twig_escape_filter($this->env, ($context["goto"] ?? null), "html", null, true);
        echo "\">
        ";
        // line 8
        echo ($context["input_for_real_end"] ?? null);
        echo "
        <input type=\"submit\" name=\"navig\" class=\"btn btn-secondary ajax\" value=\"";
        // line 9
        echo ($context["caption_output"] ?? null);
        echo "\" title=\"";
        echo twig_escape_filter($this->env, ($context["title"] ?? null), "html", null, true);
        echo "\"";
        // line 10
        echo ($context["onclick"] ?? null);
        echo ">
    </form>
</td>
";
    }

    public function getTemplateName()
    {
        return "display/results/table_navigation_button.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  75 => 10,  70 => 9,  66 => 8,  62 => 7,  58 => 6,  54 => 5,  50 => 4,  46 => 3,  40 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "display/results/table_navigation_button.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/display/results/table_navigation_button.twig");
    }
}
