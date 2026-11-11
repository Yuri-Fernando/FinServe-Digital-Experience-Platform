package br.com.finserve.aem.core.servlets;

import java.io.IOException;
import javax.servlet.ServletException;
import org.apache.sling.api.SlingHttpServletRequest;
import org.apache.sling.api.SlingHttpServletResponse;
import org.apache.sling.api.servlets.SlingSafeMethodsServlet;
import org.osgi.service.component.annotations.Component;
import org.osgi.framework.Constants;
import javax.servlet.Servlet;

/** Reference only: deploy via AEM Maven Archetype, not via standalone Python simulator. */
@Component(service = Servlet.class, property = {
    Constants.SERVICE_DESCRIPTION + "=FinServe Experience Health",
    "sling.servlet.paths=/bin/finserve/experience-health",
    "sling.servlet.methods=GET"
})
public class ExperienceHealthServlet extends SlingSafeMethodsServlet {
    private static final long serialVersionUID = 1L;
    @Override
    protected void doGet(SlingHttpServletRequest request, SlingHttpServletResponse response)
            throws ServletException, IOException {
        response.setContentType("application/json");
        response.setCharacterEncoding("UTF-8");
        response.setHeader("Cache-Control", "no-store");
        response.getWriter().write("{\"status\":\"ok\",\"service\":\"finserve-aem-reference\"}");
    }
}
