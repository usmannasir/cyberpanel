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

/* navigation/tree/path.twig */
class __TwigTemplate_dfda7334f8d4ab0e1125050c281c30d9bba9284b3d459e2a42082329e75632d8 extends \Twig\Template
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
        echo "<div class='list_container hide'>
  <ul";
        // line 2
        echo ((($context["has_search_results"] ?? null)) ? (" class=\"search_results\"") : (""));
        echo ">
    ";
        // line 3
        echo ($context["list_content"] ?? null);
        echo "
  </ul>

  ";
        // line 6
        if ( !($context["is_tree"] ?? null)) {
            // line 7
            echo "    <span class='hide loaded_db'>";
            echo twig_escape_filter($this->env, twig_urlencode_filter(($context["parent_name"] ?? null)), "html", null, true);
            echo "</span>
    ";
            // line 8
            if (twig_test_empty(($context["list_content"] ?? null))) {
                // line 9
                echo "      <div>";
                echo _gettext("No tables found in database.");
                echo "</div>
    ";
            }
            // line 11
            echo "  ";
        }
        // line 12
        echo "</div>
";
    }

    public function getTemplateName()
    {
        return "navigation/tree/path.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  68 => 12,  65 => 11,  59 => 9,  57 => 8,  52 => 7,  50 => 6,  44 => 3,  40 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "navigation/tree/path.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/navigation/tree/path.twig");
    }
}
