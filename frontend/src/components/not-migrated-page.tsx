import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function NotMigratedPage({
  title,
  fallbackHref,
}: {
  title: string;
  fallbackHref: string;
}) {
  return (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>
          This page has not been migrated to the new dashboard yet.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* Plain <a>: escapes the /app router basename for a full-page
            load of the classic Jinja2 page. */}
        <Button render={<a href={fallbackHref} />}>
          Open the classic {title} page
        </Button>
      </CardContent>
    </Card>
  );
}
