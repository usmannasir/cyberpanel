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

/* config/form_display/fieldset_bottom.twig */
class __TwigTemplate_cb423e6e09b942812f3b1b53922fd61077f4a5367b62c40b8582e1c846740ff4 extends \Twig\Template
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
        $context["colspan"] = 2;
        // line 2
        if (($context["is_setup"] ?? null)) {
            // line 3
            echo "    ";
            $context["colspan"] = (($context["colspan"] ?? null) + 1);
        }
        // line 5
        if (($context["show_buttons"] ?? null)) {
            // line 6
            echo "    <tr>
        <td colspan=\"";
            // line 7
            echo twig_escape_filter($this->env, ($context["colspan"] ?? null), "html", null, true);
            echo "\" class=\"lastrow\">
            <input class=\"btn btn-primary green\" type=\"submit\" name=\"submit_save\" value=\"";
            // line 8
            echo _gettext("Apply");
            echo "\">
            <input class=\"btn btn-secondary\" type=\"button\" name=\"submit_reset\" value=\"";
            // line 9
            echo _gettext("Reset");
            echo "\">
        </td>
    </tr>
";
        }
        // line 13
        echo "</table>
</fieldset>
";
    }

    public function getTemplateName()
    {
        return "config/form_display/fieldset_bottom.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  65 => 13,  58 => 9,  54 => 8,  50 => 7,  47 => 6,  45 => 5,  41 => 3,  39 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "config/form_display/fieldset_bottom.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/config/form_display/fieldset_bottom.twig");
    }
}
