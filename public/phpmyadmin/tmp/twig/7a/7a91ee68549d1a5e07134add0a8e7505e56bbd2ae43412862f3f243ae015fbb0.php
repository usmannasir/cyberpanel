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

/* database/structure/favorite_anchor.twig */
class __TwigTemplate_ea7d7da11bb44e25e089be8dfc13a9c95c774437ec0feef0834eca213210b891 extends \Twig\Template
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
        echo "<a id=\"";
        echo twig_escape_filter($this->env, ($context["table_name_hash"] ?? null), "html", null, true);
        echo "_favorite_anchor\"
    class=\"ajax favorite_table_anchor\"
    href=\"";
        // line 3
        echo PhpMyAdmin\Url::getFromRoute("/database/structure/favorite-table", ($context["fav_params"] ?? null));
        echo "\"
    title=\"";
        // line 4
        echo twig_escape_filter($this->env, ((($context["already_favorite"] ?? null)) ? (_gettext("Remove from Favorites")) : (_gettext("Add to Favorites"))), "html", null, true);
        echo "\"
    data-favtargets=\"";
        // line 5
        echo twig_escape_filter($this->env, ($context["db_table_name_hash"] ?? null), "html", null, true);
        echo "\">
    ";
        // line 6
        echo ((($context["already_favorite"] ?? null)) ? (\PhpMyAdmin\Html\Generator::getIcon("b_favorite")) : (\PhpMyAdmin\Html\Generator::getIcon("b_no_favorite")));
        echo "
</a>
";
    }

    public function getTemplateName()
    {
        return "database/structure/favorite_anchor.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  55 => 6,  51 => 5,  47 => 4,  43 => 3,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "database/structure/favorite_anchor.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/database/structure/favorite_anchor.twig");
    }
}
