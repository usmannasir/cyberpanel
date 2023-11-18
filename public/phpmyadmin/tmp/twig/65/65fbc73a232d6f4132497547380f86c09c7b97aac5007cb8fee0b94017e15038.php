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

/* top_menu.twig */
class __TwigTemplate_026ffaf8e358252bc1d57ffe4cec574a6bd91b4a842adc7a354b8ecdf55e3b2d extends \Twig\Template
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
        echo "<div id=\"topmenucontainer\" class=\"menucontainer\">
  <nav class=\"navbar navbar-expand-lg navbar-light bg-light\">
    <button class=\"navbar-toggler\" type=\"button\" data-toggle=\"collapse\" data-target=\"#navbarNav\" aria-label=\"";
        // line 4
        // l10n: Show or hide the menu using the hamburger style button
        echo _gettext("Toggle navigation");
        echo "\" aria-controls=\"navbarNav\" aria-expanded=\"false\">
      <span class=\"navbar-toggler-icon\"></span>
    </button>
    <div class=\"collapse navbar-collapse\" id=\"navbarNav\">
      <ul id=\"topmenu\" class=\"navbar-nav\">
        ";
        // line 9
        $context['_parent'] = $context;
        $context['_seq'] = twig_ensure_traversable(($context["tabs"] ?? null));
        foreach ($context['_seq'] as $context["_key"] => $context["tab"]) {
            // line 10
            echo "          <li class=\"nav-item";
            echo ((twig_get_attribute($this->env, $this->source, $context["tab"], "active", [], "any", false, false, false, 10)) ? (" active") : (""));
            echo "\">
            <a class=\"nav-link text-nowrap\" href=\"";
            // line 11
            echo PhpMyAdmin\Url::getFromRoute(twig_get_attribute($this->env, $this->source, $context["tab"], "route", [], "any", false, false, false, 11), twig_array_merge(($context["url_params"] ?? null), (((twig_get_attribute($this->env, $this->source, $context["tab"], "args", [], "any", true, true, false, 11) &&  !(null === twig_get_attribute($this->env, $this->source, $context["tab"], "args", [], "any", false, false, false, 11)))) ? (twig_get_attribute($this->env, $this->source, $context["tab"], "args", [], "any", false, false, false, 11)) : ([]))));
            echo "\">
              ";
            // line 12
            echo \PhpMyAdmin\Html\Generator::getIcon(twig_get_attribute($this->env, $this->source, $context["tab"], "icon", [], "any", false, false, false, 12), twig_get_attribute($this->env, $this->source, $context["tab"], "text", [], "any", false, false, false, 12), false, true, "TabsMode");
            echo "
              ";
            // line 13
            if (twig_get_attribute($this->env, $this->source, $context["tab"], "active", [], "any", false, false, false, 13)) {
                // line 14
                echo "                <span class=\"sr-only\">";
                // l10n: Current page
                echo _gettext("(current)");
                echo "</span>
              ";
            }
            // line 16
            echo "            </a>
          </li>
        ";
        }
        $_parent = $context['_parent'];
        unset($context['_seq'], $context['_iterated'], $context['_key'], $context['tab'], $context['_parent'], $context['loop']);
        $context = array_intersect_key($context, $_parent) + $_parent;
        // line 19
        echo "      </ul>
    </div>
  </nav>
</div>
";
    }

    public function getTemplateName()
    {
        return "top_menu.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  84 => 19,  76 => 16,  69 => 14,  67 => 13,  63 => 12,  59 => 11,  54 => 10,  50 => 9,  41 => 4,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "top_menu.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/top_menu.twig");
    }
}
