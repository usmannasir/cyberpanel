#!/usr/bin/ruby

$0="RACK: #{ENV['APP_NAME'] || ENV['RAILS_ROOT']} (#{ENV['RAILS_ENV']})"
if GC.respond_to?(:copy_on_write_friendly=)
    GC.copy_on_write_friendly = true
end

Dir.chdir( ENV['RAILS_ROOT'] )
app_root=ENV['RAILS_ROOT']

#use rack only
require 'fileutils'
require 'rack'
require 'lsapi'
require 'stringio'
require 'rack/content_length'
#require 'active_support'
#require 'action_controller'

module Rack
    module Handler
        class LiteSpeed
            def self.run(app, options=nil)
                while LSAPI.accept != nil
                    serve app
                end
            end
            
            def self.serve(app)
                app = Rack::ContentLength.new(app)
                env = ENV.to_hash
                env.delete "HTTP_CONTENT_LENGTH"
                env["SCRIPT_NAME"] = "" if env["SCRIPT_NAME"] == "/"
                
                rack_input = $stdin
                
                rack_input.set_encoding(Encoding::BINARY) if rack_input.respond_to?(:set_encoding)
                
                env.update(
                    "rack.version" => [1,0],
                    "rack.input" => rack_input,
                    "rack.errors" => $stderr,
                    "rack.multithread" => false,
                    "rack.multiprocess" => true,
                    "rack.run_once" => false,
                    "rack.url_scheme" => ["yes", "on", "1"].include?(ENV["HTTPS"]) ? "https" : "http"
                )
                
                env["QUERY_STRING"] ||= ""
                env["HTTP_VERSION"] ||= env["SERVER_PROTOCOL"]
                env["REQUEST_PATH"] ||= "/"
                status, headers, body = app.call(env)
                
                begin
                    if body.respond_to?(:to_path)
                        headers['X-LiteSpeed-Location'] = body.to_path
                        #headers['Content-Length'] = '0'
                        headers.delete('Content-Length') #Correct?
                        send_headers status, headers             
                    else
                        send_headers status, headers
                        send_body body
                    end
                    
                ensure
                    body.close if body.respond_to? :close
                end
            end
            
            def self.send_headers(status, headers)
                print "Status: #{status}\r\n"
                headers.each { |k, vs|
                               vs.split("\n").each { |v|
                                                     print "#{k}: #{v}\r\n"
                                                   }
                             }
                print "\r\n"
                STDOUT.flush
            end
            
            def self.send_body(body)
                body.each { |part|
                            print part
                            STDOUT.flush
                          }
            end
        end
    end
end

#
options = {
    :environment => (ENV['RAILS_ENV'] || "development").dup,
    :config => "#{app_root}/config.ru",
    :detach => false,
    :debugger => false
}
  
server = Rack::Handler::LiteSpeed
    
if File.exist?(options[:config])
    config = options[:config]
    cfgfile = File.read(config)
    app = eval("Rack::Builder.new {( " + cfgfile + "\n )}.to_app", TOPLEVEL_BINDING, config)
else
    require './config/environment'
    inner_app = ActionController::Dispatcher.new
    app = Rack::Builder.new {
        use Rails::Rack::Debugger if options[:debugger]
        run inner_app
    }.to_app
end

ActiveRecord::Base.clear_all_connections! if defined?(ActiveRecord::Base)

begin
    server.run(app, options.merge(:AccessLog => []))
ensure
    puts 'Exiting'
end

