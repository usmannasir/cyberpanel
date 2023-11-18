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

/* navigation/main.twig */
class __TwigTemplate_99dacc663ef0e5e3a73fe9e266d7e2535b4f22a9020632b6ddc10b50b52052df extends \Twig\Template
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
        if ( !($context["is_ajax"] ?? null)) {
            // line 2
            echo "  <div id=\"pma_navigation\" data-config-navigation-width=\"";
            echo twig_escape_filter($this->env, ($context["config_navigation_width"] ?? null), "html", null, true);
            echo "\">
    <div id=\"pma_navigation_resizer\"></div>
    <div id=\"pma_navigation_collapser\"></div>
    <div id=\"pma_navigation_content\">
      <div id=\"pma_navigation_header\">

        ";
            // line 8
            if (twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "is_displayed", [], "any", false, false, false, 8)) {
                // line 9
                echo "          <div id=\"pmalogo\">
            ";
                // line 10
                if (twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "has_link", [], "any", false, false, false, 10)) {
                    // line 11
                    echo "              <a href=\"";
                    echo twig_escape_filter($this->env, ((twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "link", [], "any", true, true, false, 11)) ? (_twig_default_filter(twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "link", [], "any", false, false, false, 11), "#")) : ("#")), "html", null, true);
                    echo "\"";
                    echo twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "attributes", [], "any", false, false, false, 11);
                    echo ">
            ";
                }
                // line 13
                echo "            ";
                if ( !twig_test_empty(twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "source", [], "any", false, false, false, 13))) {
                    // line 14
                    echo "              <img id=\"imgpmalogo\" src=\"";
                    echo twig_escape_filter($this->env, twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "source", [], "any", false, false, false, 14), "html", null, true);
                    echo "\" alt=\"phpMyAdmin\">
            ";
                } else {
                    // line 16
                    echo "              <h1>phpMyAdmin</h1>
            ";
                }
                // line 18
                echo "            ";
                if (twig_get_attribute($this->env, $this->source, ($context["logo"] ?? null), "has_link", [], "any", false, false, false, 18)) {
                    // line 19
                    echo "              </a>
            ";
                }
                // line 21
                echo "          </div>
        ";
            }
            // line 23
            echo "
        <div id=\"navipanellinks\">
          <a href=\"";
            // line 25
            echo PhpMyAdmin\Url::getFromRoute("/");
            echo "\" title=\"";
            echo _gettext("Home");
            echo "\">";
            // line 26
            echo \PhpMyAdmin\Html\Generator::getImage("b_home", _gettext("Home"));
            // line 27
            echo "</a>

          ";
            // line 29
            if ((($context["server"] ?? null) != 0)) {
                // line 30
                echo "            <a class=\"logout disableAjax\" href=\"";
                echo PhpMyAdmin\Url::getFromRoute("/logout");
                echo "\" title=\"";
                echo twig_escape_filter($this->env, (((($context["auth_type"] ?? null) == "config")) ? (_gettext("Empty session data")) : (_gettext("Log out"))), "html", null, true);
                echo "\">";
                // line 31
                echo \PhpMyAdmin\Html\Generator::getImage("s_loggoff", (((($context["auth_type"] ?? null) == "config")) ? (_gettext("Empty session data")) : (_gettext("Log out"))));
                // line 32
                echo "</a>
          ";
            }
            // line 34
            echo "
          <a href=\"";
            // line 35
            echo \PhpMyAdmin\Html\MySQLDocumentation::getDocumentationLink("index");
            echo "\" title=\"";
            echo _gettext("phpMyAdmin documentation");
            echo "\" target=\"_blank\" rel=\"noopener noreferrer\">";
            // line 36
            echo \PhpMyAdmin\Html\Generator::getImage("b_docs", _gettext("phpMyAdmin documentation"));
            // line 37
            echo "</a>

          <a href=\"";
            // line 39
            echo PhpMyAdmin\Util::getdocuURL(($context["is_mariadb"] ?? null));
            echo "\" title=\"";
            echo twig_escape_filter($this->env, ((($context["is_mariadb"] ?? null)) ? (_gettext("MariaDB Documentation")) : (_gettext("MySQL Documentation"))), "html", null, true);
            echo "\" target=\"_blank\" rel=\"noopener noreferrer\">";
            // line 40
            echo \PhpMyAdmin\Html\Generator::getImage("b_sqlhelp", ((($context["is_mariadb"] ?? null)) ? (_gettext("MariaDB Documentation")) : (_gettext("MySQL Documentation"))));
            // line 41
            echo "</a>

          <a id=\"pma_navigation_settings_icon\"";
            // line 43
            echo (( !($context["is_navigation_settings_enabled"] ?? null)) ? (" class=\"hide\"") : (""));
            echo " href=\"#\" title=\"";
            echo _gettext("Navigation panel settings");
            echo "\">";
            // line 44
            echo \PhpMyAdmin\Html\Generator::getImage("s_cog", _gettext("Navigation panel settings"));
            // line 45
            echo "</a>

          <a id=\"pma_navigation_reload\" href=\"#\" title=\"";
            // line 47
            echo _gettext("Reload navigation panel");
            echo "\">";
            // line 48
            echo \PhpMyAdmin\Html\Generator::getImage("s_reload", _gettext("Reload navigation panel"));
            // line 49
            echo "</a>
        </div>

        ";
            // line 52
            if ((($context["is_servers_displayed"] ?? null) && (twig_length_filter($this->env, ($context["servers"] ?? null)) > 1))) {
                // line 53
                echo "          <div id=\"serverChoice\">
            ";
                // line 54
                echo ($context["server_select"] ?? null);
                echo "
          </div>
        ";
            }
            // line 57
            echo "
        ";
            // line 58
            echo \PhpMyAdmin\Html\Generator::getImage("ajax_clock_small", _gettext("Loading…"), ["style" => "visibility: hidden; display:none", "class" => "throbber"]);
            // line 61
            echo "
      </div>
      <div id=\"pma_navigation_tree\" class=\"list_container";
            // line 63
            echo ((($context["is_synced"] ?? null)) ? (" synced") : (""));
            echo ((($context["is_highlighted"] ?? null)) ? (" highlight") : (""));
            echo ((($context["is_autoexpanded"] ?? null)) ? (" autoexpand") : (""));
            echo "\">
";
        }
        // line 65
        echo "
";
        // line 66
        if ( !($context["navigation_tree"] ?? null)) {
            // line 67
            echo "  ";
            echo call_user_func_array($this->env->getFilter('error')->getCallable(), [_gettext("An error has occurred while loading the navigation display")]);
            echo "
";
        } else {
            // line 69
            echo "  ";
            echo ($context["navigation_tree"] ?? null);
            echo "
";
        }
        // line 71
        echo "
";
        // line 72
        if ( !($context["is_ajax"] ?? null)) {
            // line 73
            echo "      </div>

      <div id=\"pma_navi_settings_container\">
        ";
            // line 76
            if (($context["is_navigation_settings_enabled"] ?? null)) {
                // line 77
                echo "          ";
                echo ($context["navigation_settings"] ?? null);
                echo "
        ";
            }
            // line 79
            echo "      </div>
    </div>

    ";
            // line 82
            if (($context["is_drag_drop_import_enabled"] ?? null)) {
                // line 83
                echo "      <div class=\"pma_drop_handler\">
        ";
                // line 84
                echo _gettext("Drop files here");
                // line 85
                echo "      </div>
      <div class=\"pma_sql_import_status\">
        <h2>
          ";
                // line 88
                echo _gettext("SQL upload");
                // line 89
                echo "          ( <span class=\"pma_import_count\">0</span> )
          <span class=\"close\">x</span>
          <span class=\"minimize\">-</span>
        </h2>
        <div></div>
      </div>
    ";
            }
            // line 96
            echo "  </div>
";
        }
    }

    public function getTemplateName()
    {
        return "navigation/main.twig";
    }

    public function isTraitable()
    {
        return false;
    }

    public function getDebugInfo()
    {
        return array (  253 => 96,  244 => 89,  242 => 88,  237 => 85,  235 => 84,  232 => 83,  230 => 82,  225 => 79,  219 => 77,  217 => 76,  212 => 73,  210 => 72,  207 => 71,  201 => 69,  195 => 67,  193 => 66,  190 => 65,  183 => 63,  179 => 61,  177 => 58,  174 => 57,  168 => 54,  165 => 53,  163 => 52,  158 => 49,  156 => 48,  153 => 47,  149 => 45,  147 => 44,  142 => 43,  138 => 41,  136 => 40,  131 => 39,  127 => 37,  125 => 36,  120 => 35,  117 => 34,  113 => 32,  111 => 31,  105 => 30,  103 => 29,  99 => 27,  97 => 26,  92 => 25,  88 => 23,  84 => 21,  80 => 19,  77 => 18,  73 => 16,  67 => 14,  64 => 13,  56 => 11,  54 => 10,  51 => 9,  49 => 8,  39 => 2,  37 => 1,);
    }

    public function getSourceContext()
    {
        return new Source("", "navigation/main.twig", "/usr/local/CyberCP/public/phpmyadmin/templates/navigation/main.twig");
    }
}
