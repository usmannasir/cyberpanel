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

/* preferences/autoload.twig */
class __TwigTemplate_8c8d85c0c5473e2d801ce51f1ed75519ece7204ad74e5f7ce7dee73093322abe extends \Twig\Template
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
        echo "<div id=\"prefs_autoload\" class=\"alert alert-primary print_ignore hide\" role=\"alert\">
    <form action=\"";
        // line 2
        echo PhpMyAdmin\Url::getFromRoute("/preferences/manage");
        echo "\" method=\"post\" class=\"disableAjax\">
        ";
        // line 3
        echo ($context["hidden_inputs"] ?? null);
        echo "
        <input type=\"hidden\" name=\"json\" value=\"\">
        <input type=\"hidden\" name=\"submit_import\" value=\"1\">
        <input type=\"hidden\" name=\"return_url\" value=\"";
        // line 6
        echo twig_escape_filter($this->env, ($context["return_url"] ?? null), "html", null, true);
        echo "\">
        ";
        // line 7
        echo _gettext("Your browser has phpMyAdmin configuration for this domain. Would you like to import it for current session?");
        // line 10
        echo "        <br>
        <a href=\"#yes\">";
        // line 11
        echo _gettext("Yes");
        echo "</a>
        / <a href=\"#no\">";
        // line 12
        echo _gettext("No");
        echo "</a>
        / <a href=\"#delete\">";
        // line 13
        echo _gettext("Delete settings");
        echo "</a>
    </form>
</div>
";
    }

    public function getTemplateName()
    {
        return "preferences/autoload.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  67 => 13,  63 => 12,  59 => 11,  56 => 10,  54 => 7,  50 => 6,  44 => 3,  40 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "preferences/autoload.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/preferences/autoload.twig");
    }
}
